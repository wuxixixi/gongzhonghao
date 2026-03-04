import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional

from collectors.base import RawItem
from collectors.arxiv_collector import ArxivCollector
from collectors.news_collector import NewsCollector
from collectors.github_collector import GithubCollector
from collectors.huggingface_collector import HuggingFaceCollector
from processors.filter import HotFilter, SelectedItem
from processors.writer import ArticleWriter, ArticleResult
from imaging.flux_generator import FluxGenerator
from publisher.draft_creator import DraftCreator
from storage.local_storage import LocalStorage
from utils.logger import get_logger

_log = get_logger("pipeline")


class Pipeline:
    """流水线编排器"""

    def __init__(self):
        self.storage = LocalStorage()
        self.filter = HotFilter()
        self.writer = ArticleWriter()
        self.image_gen = FluxGenerator()
        self.draft_creator = DraftCreator()

        # 采集器列表
        self.collectors = [
            ArxivCollector(),
            NewsCollector(),
            GithubCollector(),
            HuggingFaceCollector(),
        ]

    def run(self, skip_publish: bool = False) -> dict:
        """执行完整流水线"""
        start_time = time.time()
        report = {
            "status": "success",
            "collected_count": 0,
            "selected_count": 0,
            "article_title": "",
            "images_generated": 0,
            "draft_created": False,
            "errors": [],
            "duration_seconds": 0,  # 预设默认值
        }

        try:
            # Step 1: 并发采集
            _log.info("=" * 50)
            _log.info("开始采集...")
            items = self._collect_all()
            report["collected_count"] = len(items)

            if not items:
                report["status"] = "failed"
                report["errors"].append("采集结果为空")
                return self._finalize_report(report, start_time)

            # 保存原始数据
            self.storage.save_raw_data(items)

            # Step 2: 筛选热点
            _log.info("=" * 50)
            _log.info("开始筛选热点...")
            selected = self.filter.filter(items, top_k=10)
            report["selected_count"] = len(selected)

            if not selected:
                report["status"] = "failed"
                report["errors"].append("筛选结果为空")
                return self._finalize_report(report, start_time)

            # 保存筛选数据
            self.storage.save_selected_data(selected)

            # Step 3: 生成文章
            _log.info("=" * 50)
            _log.info("开始生成文章...")
            article = self.writer.write(selected)
            report["article_title"] = article.title

            # 保存文章
            self.storage.save_article(article)

            # Step 4: 生成配图
            _log.info("=" * 50)
            _log.info("开始生成配图...")
            images = self.image_gen.generate_all(
                cover_prompt=article.cover_prompt,
                image_prompts=article.image_prompts,
                output_dir=str(self.storage.get_today_dir()),
            )
            report["images_generated"] = (
                (1 if images["cover"] else 0) + len(images["images"])
            )

            # Step 5: 发布草稿
            if not skip_publish:
                _log.info("=" * 50)
                _log.info("开始发布草稿...")
                try:
                    draft_id = self.draft_creator.create_draft(
                        article=article,
                        cover_image_path=images.get("cover"),
                        inline_images=images.get("images", []),
                    )
                    report["draft_created"] = bool(draft_id)
                except Exception as e:
                    _log.warning("发布失败（文章已保存到本地）: %s", e)
                    report["errors"].append(f"发布失败: {e}")
            else:
                _log.info("跳过发布步骤")

        except Exception as e:
            _log.error("流水线执行异常: %s", e)
            report["status"] = "failed"
            report["errors"].append(str(e))

        return self._finalize_report(report, start_time)

    def _finalize_report(self, report: dict, start_time: float) -> dict:
        """完成报告并保存"""
        report["duration_seconds"] = round(time.time() - start_time, 2)
        self.storage.save_run_report(report)

        _log.info("=" * 50)
        _log.info("流水线执行完成: %s", report["status"])
        _log.info("耗时: %.2f 秒", report["duration_seconds"])

        return report

    def _collect_all(self) -> List[RawItem]:
        """并发采集所有数据源"""
        all_items: List[RawItem] = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(collector.collect): collector.name
                for collector in self.collectors
            }

            for future in as_completed(futures):
                name = futures[future]
                try:
                    items = future.result()
                    _log.info("%s 采集完成: %d 条", name, len(items))
                    all_items.extend(items)
                except Exception as e:
                    _log.error("%s 采集失败: %s", name, e)

        return all_items
