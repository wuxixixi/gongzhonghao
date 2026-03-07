import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.collectors.base import RawItem
from app.collectors.arxiv_collector import ArxivCollector
from app.collectors.news_collector import NewsCollector
from app.collectors.github_collector import GithubCollector
from app.collectors.huggingface_collector import HuggingFaceCollector
from app.processors.filter import HotFilter, SelectedItem
from app.processors.multi_stage_filter import create_multi_stage_filter, MultiStageFilterAdapter
from app.processors.writer import ArticleWriter, ArticleResult
from app.imaging.image_generator import ImageGenerator
from app.publisher.draft_creator import DraftCreator
from app.storage.local_storage import LocalStorage
from app.utils.logger import get_logger

_log = get_logger("pipeline")


class Pipeline:
    """流水线编排器"""

    def __init__(self, use_multi_stage_filter: bool = True):
        self.storage = LocalStorage()
        
        # 使用多级筛选器（推荐）
        if use_multi_stage_filter:
            self.filter = create_multi_stage_filter(
                stage4_sample_size=15,
                final_output_size=10,
            )
            _log.info("使用 MultiStageFilter 多级筛选器")
        else:
            self.filter = HotFilter()
            _log.info("使用 HotFilter 传统筛选器")
        
        self.writer = ArticleWriter()
        # 使用统一图片生成器（支持多提供商自动切换）
        self.image_gen = ImageGenerator()
        self.draft_creator = DraftCreator()

        # 采集器列表
        self.collectors = [
            ArxivCollector(),
            NewsCollector(),
            GithubCollector(),
            HuggingFaceCollector(),
        ]

    def _load_existing_article(self) -> Optional[ArticleResult]:
        """检查并加载已有文章"""
        article_md = self.storage.get_today_dir() / "article.md"
        article_html = self.storage.get_today_dir() / "article.html"

        if not article_md.exists():
            return None

        _log.info("发现已有文章: %s", article_md)

        # 读取文章内容
        with open(article_md, "r", encoding="utf-8") as f:
            content_md = f.read()

        with open(article_html, "r", encoding="utf-8") as f:
            content_html = f.read()

        # 提取标题（第一行 # 开头）
        lines = content_md.strip().split("\n")
        title = lines[0].replace("#", "").strip() if lines else "AI日报"

        # 提取摘要（从 selected_data.json）
        import json
        selected_data_path = self.storage.get_today_dir() / "selected_data.json"
        digest = ""
        if selected_data_path.exists():
            try:
                with open(selected_data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        digest = f"今日AI热点速览，共{len(data)}条精选资讯"
            except:
                pass

        # 检查已有图片
        cover_path = self.storage.get_today_dir() / "cover.png"
        image_paths = []
        for i in range(1, 4):
            img_path = self.storage.get_today_dir() / f"image_{i}.png"
            if img_path.exists():
                image_paths.append(str(img_path))

        return ArticleResult(
            title=title,
            content_markdown=content_md,
            content_html=content_html,
            digest=digest,
            cover_prompt="AI technology, digital art, futuristic",
            image_prompts=["AI technology illustration"] * 3,
        ), str(cover_path) if cover_path.exists() else None, image_paths

    def run(self, skip_publish: bool = False, force_regenerate: bool = False) -> dict:
        """
        执行完整流水线

        Args:
            skip_publish: 是否跳过发布步骤
            force_regenerate: 是否强制重新生成（忽略已有文章）
        """
        start_time = time.time()
        report = {
            "status": "success",
            "collected_count": 0,
            "selected_count": 0,
            "article_title": "",
            "images_generated": 0,
            "draft_created": False,
            "errors": [],
            "duration_seconds": 0,
            "from_cache": False,
        }

        try:
            # 检查是否已有文章
            if not force_regenerate:
                existing = self._load_existing_article()
                if existing:
                    article, cover_path, image_paths = existing
                    report["article_title"] = article.title
                    report["from_cache"] = True
                    _log.info("使用已有文章，跳过采集和写作")

                    # 检查图片数量
                    report["images_generated"] = (1 if cover_path else 0) + len(image_paths)

                    # 直接进入发布步骤
                    if not skip_publish:
                        _log.info("=" * 50)
                        _log.info("开始发布草稿...")
                        try:
                            draft_id = self.draft_creator.create_draft(
                                article=article,
                                cover_image_path=cover_path,
                                inline_images=image_paths,
                            )
                            report["draft_created"] = bool(draft_id)
                        except Exception as e:
                            _log.warning("发布失败: %s", e)
                            report["errors"].append(f"发布失败: {e}")
                    else:
                        _log.info("跳过发布步骤")

                    return self._finalize_report(report, start_time)

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
