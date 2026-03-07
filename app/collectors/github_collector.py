import re
from datetime import datetime
from typing import List

import requests
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector, RawItem
from app.utils.logger import get_logger
from app.utils.proxy import requests_with_proxy

_log = get_logger("github_collector")


# NLP 相关关键词，用于过滤仓库 - 聚焦自然语言处理方向
NLP_KEYWORDS = re.compile(
    r"\b(nlp|natural.?language|llm|large.?language|transformer|bert|gpt|"
    r"text.?classification|ner|pos.?tagging|parsing|sentiment|question.?answer|"
    r"text.?generation|embedding|tokenizer|llama|chatgpt|language.?model|"
    r"seq2seq|text.?understanding|dialogue|conversation|translation|machine.?translat|"
    r"text.?summariz|information.?extract|knowledge.?graph|rag|langchain|peft|"
    r"instruction.?tuning|rlhf|DPO|word.?vector|word2vec|token)\b",
    re.IGNORECASE,
)


class GithubCollector(BaseCollector):

    name = "github"
    
    # 覆盖基类配置
    rate_limit_delay = 1.0  # GitHub 限制更严格
    timeout = 30

    TRENDING_URL = "https://github.com/trending?since=daily&spoken_language_code="
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def _do_collect(self) -> List[RawItem]:
        """执行 GitHub Trending 采集"""
        items: List[RawItem] = []

        resp = requests_with_proxy(self.TRENDING_URL, headers=self.HEADERS, timeout=self.timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = soup.select("article.Box-row")
        _log.debug("GitHub Trending 解析到 %d 个仓库", len(rows))

        for row in rows:
            # 限流
            self._rate_limit()
            
            try:
                item = self._parse_row(row)
                if item:
                    items.append(item)
            except Exception as e:
                _log.debug("解析仓库行失败: %s", e)
                continue

        return items

    def _parse_row(self, row) -> RawItem | None:
        # 仓库名
        h2 = row.select_one("h2 a")
        if not h2:
            return None
        repo_path = h2.get("href", "").strip("/")
        repo_name = repo_path.split("/")[-1] if "/" in repo_path else repo_path

        # 描述
        desc_tag = row.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 星标数
        star_tag = row.select_one("a[href$='/stargazers']")
        stars = star_tag.get_text(strip=True).replace(",", "") if star_tag else "0"

        # 语言
        lang_tag = row.select_one("[itemprop='programmingLanguage']")
        language = lang_tag.get_text(strip=True) if lang_tag else ""

        # 判断是否 NLP 相关
        text_to_check = f"{repo_name} {description} {language}"
        if not NLP_KEYWORDS.search(text_to_check):
            return None

        url = f"https://github.com/{repo_path}"
        summary = f"{description} | Stars: {stars} | Language: {language}"

        return RawItem(
            source="github",
            title=repo_path,
            summary=summary[:300],
            url=url,
            published_at=datetime.now(),
            tags=["github", language.lower()] if language else ["github"],
            extra={
                "stars": int(stars) if stars.isdigit() else 0,
                "language": language,
            }
        )
