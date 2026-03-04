import json
from datetime import datetime
from pathlib import Path
from typing import List, Any

from collectors.base import RawItem
from processors.filter import SelectedItem
from processors.writer import ArticleResult
from config.settings import OUTPUT_BASE_DIR
from utils.logger import get_logger

_log = get_logger("storage")


class LocalStorage:
    """本地存储管理器"""

    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or OUTPUT_BASE_DIR
        self.today_dir: Path = None
        self.deep_analysis_dir: Path = None
        self._ensure_today_dir()

    def _ensure_today_dir(self):
        """确保当天目录存在"""
        today = datetime.now().strftime("%y%m%d")
        self.today_dir = self.base_dir / today
        self.today_dir.mkdir(parents=True, exist_ok=True)

        # 创建深度分析子目录
        self.deep_analysis_dir = self.today_dir / "深度分析"
        self.deep_analysis_dir.mkdir(parents=True, exist_ok=True)

        _log.debug("今日目录: %s", self.today_dir)
        _log.debug("深度分析目录: %s", self.deep_analysis_dir)

    def get_today_dir(self) -> Path:
        """获取当天输出目录"""
        return self.today_dir

    def get_deep_analysis_dir(self) -> Path:
        """获取深度分析目录"""
        return self.deep_analysis_dir

    def save_raw_data(self, items: List[RawItem]) -> str:
        """保存原始采集数据"""
        path = self.today_dir / "raw_data.json"
        data = [item.to_dict() for item in items]
        self._write_json(path, data)
        _log.info("保存原始数据: %s (%d 条)", path, len(items))
        return str(path)

    def save_selected_data(self, items: List[SelectedItem]) -> str:
        """保存筛选后数据"""
        path = self.today_dir / "selected_data.json"
        data = [
            {
                "title": item.raw.title,
                "source": item.raw.source,
                "score": item.score,
                "reason": item.reason,
                "category": item.category,
                "url": item.raw.url,
            }
            for item in items
        ]
        self._write_json(path, data)
        _log.info("保存筛选数据: %s (%d 条)", path, len(items))
        return str(path)

    def save_article(self, article: ArticleResult, deep_analysis: bool = False) -> tuple[str, str]:
        """保存文章（Markdown + HTML）

        Args:
            article: 文章结果
            deep_analysis: 是否保存到深度分析目录
        """
        if deep_analysis:
            output_dir = self.deep_analysis_dir
        else:
            output_dir = self.today_dir

        md_path = output_dir / "article.md"
        html_path = output_dir / "article.html"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {article.title}\n\n")
            f.write(article.content_markdown)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(f"<h1>{article.title}</h1>\n")
            f.write(article.content_html)

        _log.info("保存文章: %s, %s", md_path, html_path)
        return str(md_path), str(html_path)

    def save_original_content(self, title: str, content: str) -> str:
        """保存原文内容

        Args:
            title: 文章标题
            content: 原文内容

        Returns:
            保存的文件路径
        """
        import re
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', title)[:50]
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"原文_{timestamp}_{safe_title}.md"

        file_path = self.deep_analysis_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        _log.info("保存原文: %s", file_path)
        return str(file_path)

    def save_run_report(self, report: dict) -> str:
        """保存运行报告"""
        path = self.today_dir / "run_report.json"
        report["generated_at"] = datetime.now().isoformat()
        self._write_json(path, report)
        _log.info("保存运行报告: %s", path)
        return str(path)

    def _write_json(self, path: Path, data: Any):
        """写入 JSON 文件"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
