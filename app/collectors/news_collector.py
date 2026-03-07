from datetime import datetime
from typing import List

from tavily import TavilyClient

from app.collectors.base import BaseCollector, RawItem
from app.config.settings import TAVILY_API_KEY
from app.utils.logger import get_logger

_log = get_logger("news_collector")


class NewsCollector(BaseCollector):
    """使用 Tavily 搜索引擎采集 NLP 新闻"""

    name = "news"
    
    # 覆盖基类配置
    rate_limit_delay = 0.5
    timeout = 30

    # NLP 相关搜索关键词
    SEARCH_QUERIES = [
        "NLP natural language processing latest breakthrough",
        "LLM large language model new research 2024 2025",
        "text classification NER sentiment analysis research",
        "transformer BERT GPT architecture research paper",
        "大语言模型 NLP 中文自然语言处理 最新进展",
    ]

    def __init__(self):
        super().__init__()
        self._client = TavilyClient(api_key=TAVILY_API_KEY)

    def _do_collect(self) -> List[RawItem]:
        """执行新闻采集"""
        seen_urls: set = set()
        items: List[RawItem] = []

        for query in self.SEARCH_QUERIES:
            # 限流
            self._rate_limit()
            
            _log.debug("搜索: %s", query)

            response = self._client.search(
                query=query,
                search_depth="basic",
                max_results=10,
                include_raw_content=False,
                topic="news",
            )

            for result in response.get("results", []):
                url = result.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title = result.get("title", "")
                content = result.get("content", "")[:300]

                items.append(RawItem(
                    source="news",
                    title=title,
                    summary=content,
                    url=url,
                    published_at=datetime.now(),
                    tags=["news", "tavily"],
                    extra={
                        "query": query,
                    }
                ))

            _log.debug("查询 '%s' 返回 %d 条", query, len(response.get("results", [])))

        return items
