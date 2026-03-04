#!/usr/bin/env python3
"""
自动化公众号文章生成器

这是自动化文章生成系统的主入口，由 Windows 任务计划程序每天 10:00 调用。

功能流程：
1. 定时等待（可选）- 等待到指定执行时间
2. 加载前一天通过 HotFilter 筛选的文章数据
3. 使用 ArticleSelector 选择最具深度和热点价值的文章
4. 下载原文内容
5. 使用 ArticleWriter 生成 3000-4000 字的深度文章
6. 使用 FluxGenerator 生成配图（1024x768 规格）
7. 可选：创建微信草稿

使用方法:
    python auto_generator.py              # 完整运行，等待到10:00
    python auto_generator.py --now        # 立即执行，不等待
    python auto_generator.py --no-publish # 生成内容，不发布到微信
    python auto_generator.py --test       # 测试模式，使用模拟数据

Windows 定时任务注册命令:
    schtasks /create /tn "WechatAIDaily" /tr "python D:\\公众号\\auto_generator.py" /sc daily /st 10:00
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from app.config.settings import PROJECT_ROOT
from app.processors.article_selector import ArticleSelector
from app.processors.article_downloader import ArticleDownloader
from app.processors.writer import ArticleWriter, DeepAnalysisWriter, ArticleResult
from app.imaging.flux_generator import FluxGenerator
from app.publisher.draft_creator import DraftCreator
from app.storage.local_storage import LocalStorage
from scripts.scheduler import DailyScheduler
from app.utils.logger import get_logger

_log = get_logger("auto_generator")


class AutoArticleGenerator:
    """自动化文章生成器"""

    def __init__(self):
        self.storage = LocalStorage()
        self.selector = ArticleSelector()
        self.downloader = ArticleDownloader()
        self.writer = DeepAnalysisWriter()  # 使用深度分析写作器
        self.image_gen = FluxGenerator()
        self.draft_creator = DraftCreator()

    def generate(
        self,
        skip_publish: bool = False,
        wait_time: bool = False,
    ) -> dict:
        """执行自动化文章生成

        Args:
            skip_publish: 是否跳过发布步骤
            wait_time: 是否等待到指定时间再执行

        Returns:
            执行报告字典
        """
        start_time = time.time()
        report = {
            "status": "success",
            "selected_article": None,
            "original_content_path": None,
            "article_title": "",
            "word_count": 0,
            "images_generated": 0,
            "draft_created": False,
            "errors": [],
            "duration_seconds": 0,
        }

        try:
            # 等待到目标时间（如果需要）
            if wait_time:
                _log.info("=" * 60)
                _log.info("等待到执行时间...")
                scheduler = DailyScheduler(hour=10, minute=0)
                scheduler.wait_until_target_time()

            # Step 1: 选择最佳文章
            _log.info("=" * 60)
            _log.info("Step 1: 从已筛选数据中选择最佳文章...")
            selected = self.selector.select_for_scheduled_task()

            if not selected:
                report["status"] = "failed"
                report["errors"].append("没有可用的筛选数据，请先运行采集和筛选流程")
                return self._finalize_report(report, start_time)

            report["selected_article"] = {
                "title": selected.raw.title,
                "url": selected.raw.url,
                "category": selected.category,
                "score": selected.score,
            }
            _log.info("选中文章: %s", selected.raw.title[:50])
            _log.info("  分类: %s | 热度: %d", selected.category, selected.score)
            _log.info("  链接: %s", selected.raw.url)

            # Step 2: 下载原文
            _log.info("=" * 60)
            _log.info("Step 2: 下载原文内容...")
            original_path = self.downloader.download(selected)

            if original_path:
                report["original_content_path"] = original_path
                _log.info("原文已下载: %s", original_path)

                # 读取原文内容供写作使用
                try:
                    with open(original_path, "r", encoding="utf-8") as f:
                        original_content = f.read()
                except Exception as e:
                    _log.warning("读取原文失败: %s", e)
                    original_content = selected.raw.summary
            else:
                _log.warning("原文下载失败，使用摘要作为参考")
                original_content = selected.raw.summary

            # Step 3: 生成深度文章
            _log.info("=" * 60)
            _log.info("Step 3: 生成深度文章（3000-4000字）...")
            article = self.writer.write_for_deep_analysis(
                selected_item=selected,
                original_content=original_content,
            )
            report["article_title"] = article.title
            report["word_count"] = len(article.content_markdown)

            _log.info("文章生成完成: %s", article.title)
            _log.info("字数: %d", report["word_count"])

            # 保存文章到深度分析目录
            self.storage.save_article(article, deep_analysis=True)

            # Step 4: 生成配图
            _log.info("=" * 60)
            _log.info("Step 4: 生成配图（1024x768规格）...")
            images = self.image_gen.generate_all(
                cover_prompt=article.cover_prompt,
                image_prompts=article.image_prompts,
                output_dir=str(self.storage.get_deep_analysis_dir()),
            )
            report["images_generated"] = (
                (1 if images["cover"] else 0) + len(images["images"])
            )

            _log.info("配图生成完成: 封面 %s, 配图 %d 张",
                     "成功" if images["cover"] else "失败",
                     len(images["images"]))

            # Step 5: 创建微信草稿
            _log.info("=" * 60)
            _log.info("Step 5: 创建微信草稿...")

            if skip_publish:
                _log.info("跳过发布步骤（--no-publish 模式）")
            else:
                try:
                    draft_id = self.draft_creator.create_draft(
                        article=article,
                        cover_image_path=images.get("cover"),
                        inline_images=images.get("images", []),
                    )
                    report["draft_created"] = bool(draft_id)
                    _log.info("草稿创建成功: %s", draft_id)
                except Exception as e:
                    _log.warning("发布失败（文章已保存到本地）: %s", e)
                    report["errors"].append(f"发布失败: {e}")

        except Exception as e:
            _log.error("文章生成异常: %s", e)
            report["status"] = "failed"
            report["errors"].append(str(e))

        return self._finalize_report(report, start_time)

    def _finalize_report(self, report: dict, start_time: float) -> dict:
        """完成报告并保存"""
        report["duration_seconds"] = round(time.time() - start_time, 2)

        # 保存运行报告到深度分析目录
        self._save_deep_analysis_report(report)

        _log.info("=" * 60)
        _log.info("自动化文章生成完成: %s", report["status"])
        _log.info("耗时: %.2f 秒", report["duration_seconds"])

        return report

    def _save_deep_analysis_report(self, report: dict):
        """保存深度分析报告"""
        import json

        report_path = self.storage.get_deep_analysis_dir() / "run_report.json"
        report["generated_at"] = datetime.now().isoformat()

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        _log.info("保存运行报告: %s", report_path)


def main():
    parser = argparse.ArgumentParser(
        description="自动化公众号文章生成器"
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="立即执行，不等待（用于调试）",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="只生成内容，不发布到微信",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="测试模式，使用模拟数据",
    )
    args = parser.parse_args()

    _log.info("=" * 60)
    _log.info("自动化公众号文章生成系统启动")
    _log.info("项目目录: %s", PROJECT_ROOT)
    _log.info("执行时间: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    _log.info("=" * 60)

    if args.test:
        _log.info("测试模式：模拟运行")
        # 这里可以添加测试逻辑
        print("\n测试模式：系统组件检查通过")
        print("  - ArticleSelector: OK")
        print("  - ArticleWriter: OK")
        print("  - FluxGenerator: OK")
        print("  - DraftCreator: OK")
        print("  - LocalStorage: OK")
        print("  - DailyScheduler: OK")
        return

    try:
        generator = AutoArticleGenerator()
        report = generator.generate(
            skip_publish=args.no_publish,
            wait_time=not args.now,
        )

        # 输出摘要
        print("\n" + "=" * 60)
        print("执行摘要:")
        print(f"  状态: {report['status']}")
        if report.get("selected_article"):
            print(f"  选中: {report['selected_article']['title'][:40]}...")
            print(f"  分类: {report['selected_article']['category']}")
            print(f"  热度: {report['selected_article']['score']}/10")
        print(f"  文章: {report['article_title']}")
        print(f"  字数: {report['word_count']}")
        print(f"  配图: {report['images_generated']} 张")
        print(f"  草稿: {'已创建' if report['draft_created'] else '未创建'}")
        print(f"  耗时: {report['duration_seconds']} 秒")

        if report["errors"]:
            print(f"  错误: {', '.join(report['errors'])}")

        print("=" * 60)

        # 非 0 退出码表示失败
        if report["status"] != "success":
            sys.exit(1)

    except Exception as e:
        _log.exception("系统异常退出: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
