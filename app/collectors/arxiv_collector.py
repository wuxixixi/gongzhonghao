import time
from datetime import datetime, timedelta, timezone
from typing import List

import arxiv

from app.collectors.base import BaseCollector, RawItem
from app.config.settings import ARXIV_MAX_RESULTS
from app.utils.logger import get_logger

_log = get_logger("arxiv_collector")


class ArxivCollector(BaseCollector):

    name = "arxiv"
    
    # 覆盖基类配置
    rate_limit_delay = 0.2  # arXiv 请求间隔
    timeout = 60  # arXiv 可能较慢

    # 关注的分类 - 聚焦 NLP 方向
    CATEGORIES = ["cs.CL", "cs.AI"]  # cs.CL=计算语言学, cs.AI=人工智能(包含NLP相关)

    def _do_collect(self) -> List[RawItem]:
        """执行 arXiv 论文采集"""
        query = " OR ".join(f"cat:{c}" for c in self.CATEGORIES)

        client = arxiv.Client(page_size=ARXIV_MAX_RESULTS, delay_seconds=1.0)
        search = arxiv.Search(
            query=query,
            max_results=ARXIV_MAX_RESULTS,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        items: List[RawItem] = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

        for result in client.results(search):
            # 过滤：只取最近 48h 内提交的（arXiv 有延迟）
            pub_date = result.published.replace(tzinfo=timezone.utc)
            if pub_date < cutoff:
                continue

            summary = result.summary.replace("\n", " ")[:300]
            tags = [c for c in (result.primary_category or "").split(".") if c]

            items.append(RawItem(
                source="arxiv",
                title=result.title,
                summary=summary,
                url=result.entry_id,
                published_at=pub_date.replace(tzinfo=None),
                tags=tags,
                extra={
                    "authors": [a.name for a in result.authors[:3]],
                    "categories": result.categories,
                }
            ))
            
            # 限流
            time.sleep(0.1)

        return items
