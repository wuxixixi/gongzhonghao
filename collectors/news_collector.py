from datetime import datetime
from typing import List

from tavily import TavilyClient

from collectors.base import BaseCollector, RawItem
from config.settings import TAVILY_API_KEY
from utils.logger import get_logger

_log = get_logger("news_collector")


class NewsCollector(BaseCollector):
    """使用 Tavily 搜索引擎采集 AI 新闻"""

    name = "news"

    # AI 相关搜索关键词
    SEARCH_QUERIES = [
        "AI artificial intelligence latest news today",
        "LLM large language model breakthrough",
        "OpenAI GPT Claude Gemini new release",
        "人工智能 AI 最新突破和进展",
    ]

    def __init__(self):
        self.client = TavilyClient(api_key=TAVILY_API_KEY)

    def collect(self) -> List[RawItem]:
        """执行采集"""
        _log.info("开始采集 AI 新闻 (Tavily)")
        seen_urls: set = set()
        items: List[RawItem] = []

        for query in self.SEARCH_QUERIES:
            try:
                _log.debug("搜索: %s", query)

                response = self.client.search(
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
                    ))

                _log.debug("查询 '%s' 返回 %d 条", query, len(response.get("results", [])))

            except Exception as e:
                _log.warning("搜索 '%s' 失败: %s", query, e)
                continue

        _log.info("AI 新闻采集完成，共 %d 条 (去重后)", len(items))
        return items
