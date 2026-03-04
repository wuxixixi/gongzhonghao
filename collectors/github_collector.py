import re
from datetime import datetime
from typing import List

import requests
from bs4 import BeautifulSoup

from collectors.base import BaseCollector, RawItem
from utils.logger import get_logger

_log = get_logger("github_collector")

# AI 相关关键词，用于过滤仓库
AI_KEYWORDS = re.compile(
    r"\b(ai|ml|llm|gpt|transformer|neural|deep.?learn|machine.?learn|"
    r"diffusion|agent|rag|langchain|embedding|nlp|vision|multimodal)\b",
    re.IGNORECASE,
)


class GithubCollector(BaseCollector):

    name = "github"

    TRENDING_URL = "https://github.com/trending?since=daily"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def collect(self) -> List[RawItem]:
        _log.info("开始采集 GitHub Trending")
        items: List[RawItem] = []

        try:
            resp = requests.get(self.TRENDING_URL, headers=self.HEADERS, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            rows = soup.select("article.Box-row")
            _log.info("GitHub Trending 解析到 %d 个仓库", len(rows))

            for row in rows:
                try:
                    item = self._parse_row(row)
                    if item:
                        items.append(item)
                except Exception as e:
                    _log.debug("解析仓库行失败: %s", e)
                    continue

        except Exception as e:
            _log.error("GitHub Trending 采集失败: %s", e)

        _log.info("GitHub Trending 采集完成 (AI 相关)，共 %d 条", len(items))
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

        # 判断是否 AI 相关
        text_to_check = f"{repo_name} {description} {language}"
        if not AI_KEYWORDS.search(text_to_check):
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
        )
