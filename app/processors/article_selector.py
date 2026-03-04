"""
文章选择器模块

从已筛选的热点文章中选择最具深度和热点价值的文章进行深入分析。
主要考虑因素：
1. 热度评分 - 体现热点价值
2. 内容深度 - 技术解析、原理说明、行业洞察
3. 可扩展性 - 是否有多角度分析的空间
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from app.processors.filter import SelectedItem
from app.config.settings import OUTPUT_BASE_DIR
from app.utils.logger import get_logger

_log = get_logger("article_selector")


class ArticleSelector:
    """文章选择器 - 从已筛选数据中选择最适合深入分析的文章"""

    # 深度评分权重
    DEPTH_WEIGHTS = {
        "大模型": 1.2,          # 大模型通常有更多可分析的内容
        "开源项目": 1.1,        # 开源项目有代码可分析
        "学术研究": 1.3,        # 学术研究有论文可解读
        "应用落地": 1.0,        # 应用落地案例
        "行业分析": 1.15,       # 行业分析有洞察空间
    }

    def __init__(self):
        self.base_dir = OUTPUT_BASE_DIR

    def select_best_article(self, items: List[SelectedItem]) -> Optional[SelectedItem]:
        """从已筛选的文章中选择最佳文章

        选择标准：
        1. 综合评分 = 热度评分 * 深度权重
        2. 优先选择有技术深度的内容
        3. 考虑文章的可扩展性和分析空间

        Args:
            items: 已筛选的文章列表

        Returns:
            最佳选择的文章，如果为空返回 None
        """
        if not items:
            _log.warning("没有可选择的文章")
            return None

        _log.info("开始选择最佳文章，候选数量: %d", len(items))

        # 计算每篇文章的综合评分
        scored_items = []
        for item in items:
            depth_weight = self.DEPTH_WEIGHTS.get(item.category, 1.0)
            # 综合评分 = 热度 * 深度权重
            composite_score = item.score * depth_weight

            scored_items.append({
                "item": item,
                "composite_score": composite_score,
                "depth_weight": depth_weight,
            })

            _log.debug(
                "文章评分: %s | 热度:%d * 深度权重:%.2f = 综合分:%.2f",
                item.raw.title[:30],
                item.score,
                depth_weight,
                composite_score
            )

        # 按综合评分降序排序
        scored_items.sort(key=lambda x: x["composite_score"], reverse=True)

        # 选择最佳文章
        best = scored_items[0]
        _log.info(
            "最佳选择: %s (综合评分: %.2f)",
            best["item"].raw.title[:50],
            best["composite_score"]
        )

        return best["item"]

    def load_yesterday_selected_data(self) -> List[SelectedItem]:
        """加载前一天已筛选的数据

        用于定时任务场景：从昨天的筛选结果中选择文章

        Returns:
            已筛选的文章列表
        """
        # 计算昨天的日期目录
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_dir = self.base_dir / yesterday.strftime("%y%m%d")

        if not yesterday_dir.exists():
            _log.warning("昨天的数据目录不存在: %s", yesterday_dir)
            return []

        selected_file = yesterday_dir / "selected_data.json"
        if not selected_file.exists():
            _log.warning("昨天的筛选数据文件不存在: %s", selected_file)
            return []

        try:
            with open(selected_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 转换为 SelectedItem（需要重新构建 RawItem）
            items = []
            for item_data in data:
                from app.collectors.base import RawItem
                raw = RawItem(
                    title=item_data.get("title", ""),
                    url=item_data.get("url", ""),
                    summary="",  # 摘要可能未保存
                    source=item_data.get("source", "unknown"),
                )
                selected = SelectedItem(
                    raw=raw,
                    score=item_data.get("score", 5),
                    reason=item_data.get("reason", ""),
                    category=item_data.get("category", ""),
                )
                items.append(selected)

            _log.info("加载昨天筛选数据: %d 条 from %s", len(items), yesterday_dir.name)
            return items

        except Exception as e:
            _log.error("加载昨天筛选数据失败: %s", e)
            return []

    def load_today_selected_data(self) -> List[SelectedItem]:
        """加载当天的已筛选数据（当天已运行过筛选流程）

        Returns:
            已筛选的文章列表
        """
        today = datetime.now()
        today_dir = self.base_dir / today.strftime("%y%m%d")

        if not today_dir.exists():
            _log.warning("今天的数据目录不存在: %s", today_dir)
            return []

        selected_file = today_dir / "selected_data.json"
        if not selected_file.exists():
            _log.warning("今天的筛选数据文件不存在: %s", selected_file)
            return []

        try:
            with open(selected_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            items = []
            for item_data in data:
                from app.collectors.base import RawItem
                raw = RawItem(
                    title=item_data.get("title", ""),
                    url=item_data.get("url", ""),
                    summary="",
                    source=item_data.get("source", "unknown"),
                )
                selected = SelectedItem(
                    raw=raw,
                    score=item_data.get("score", 5),
                    reason=item_data.get("reason", ""),
                    category=item_data.get("category", ""),
                )
                items.append(selected)

            _log.info("加载今天筛选数据: %d 条 from %s", len(items), today_dir.name)
            return items

        except Exception as e:
            _log.error("加载今天筛选数据失败: %s", e)
            return []

    def select_for_scheduled_task(self) -> Optional[SelectedItem]:
        """为定时任务选择文章

        优先使用昨天的筛选数据（因为定时任务在第二天执行）
        如果昨天没有数据，则尝试使用今天的数据

        Returns:
            最佳选择的文章
        """
        # 首先尝试昨天的数据
        items = self.load_yesterday_selected_data()

        if items:
            _log.info("使用昨天筛选数据进行文章选择")
            return self.select_best_article(items)

        # 如果昨天没有数据，尝试今天的数据
        items = self.load_today_selected_data()
        if items:
            _log.info("使用今天筛选数据进行文章选择")
            return self.select_best_article(items)

        _log.error("没有可用的筛选数据")
        return None


def select_article_from_file(file_path: str) -> Optional[SelectedItem]:
    """从指定的筛选数据文件选择最佳文章

    Args:
        file_path: 筛选数据 JSON 文件路径

    Returns:
        最佳选择的文章
    """
    selector = ArticleSelector()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = []
        for item_data in data:
            from app.collectors.base import RawItem
            raw = RawItem(
                title=item_data.get("title", ""),
                url=item_data.get("url", ""),
                summary="",
                source=item_data.get("source", "unknown"),
            )
            selected = SelectedItem(
                raw=raw,
                score=item_data.get("score", 5),
                reason=item_data.get("reason", ""),
                category=item_data.get("category", ""),
            )
            items.append(selected)

        return selector.select_best_article(items)

    except Exception as e:
        _log.error("从文件选择文章失败: %s", e)
        return None
