from datetime import datetime, timezone, timedelta
from typing import List

import requests

from app.collectors.base import BaseCollector, RawItem
from app.config.settings import HF_MODELS_LIMIT
from app.utils.proxy import requests_with_proxy
from app.utils.logger import get_logger

_log = get_logger("hf_collector")


class HuggingFaceCollector(BaseCollector):

    name = "huggingface"

    API_URL = "https://huggingface.co/api/models"

    # NLP 相关的 pipeline tags
    NLP_PIPELINE_TAGS = {
        "text-generation", "text2text-generation", "conversational",
        "question-answering", "summarization", "translation",
        "token-classification", "text-classification", "sentiment-analysis",
        "fill-mask", "ner", "pos-tagging", "parsing",
        "text-to-speech", "automatic-speech-recognition",
        "embeddings", "feature-extraction",
    }

    # NLP 相关的关键词标签
    NLP_TAGS = {
        "nlp", "text", "language", "llm", "transformer", "language-model",
        "text-generation", "text-classification", "token-classification",
        "question-answering", "summarization", "translation", "conversational",
    }

    def collect(self) -> List[RawItem]:
        _log.info("开始采集 HuggingFace 最新模型")
        items: List[RawItem] = []

        try:
            resp = requests_with_proxy(
                self.API_URL,
                params={
                    "sort": "createdAt",
                    "direction": "-1",
                    "limit": HF_MODELS_LIMIT,
                },
                timeout=30,
            )
            resp.raise_for_status()
            models = resp.json()

            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

            for m in models:
                model_id = m.get("modelId", "") or m.get("id", "")
                created = m.get("createdAt", "")
                likes = m.get("likes", 0)
                downloads = m.get("downloads", 0)
                pipeline_tag = m.get("pipeline_tag", "")
                tags = m.get("tags", [])

                # 过滤：只取近期 + 有一定关注度
                if created:
                    try:
                        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        if created_dt < cutoff:
                            continue
                    except ValueError:
                        pass

                if likes < 5 and downloads < 50:
                    continue

                # 过滤：只保留 NLP 相关的模型
                is_nlp = (
                    (pipeline_tag and pipeline_tag in self.NLP_PIPELINE_TAGS) or
                    any(tag.lower() in self.NLP_TAGS for tag in tags)
                )
                if not is_nlp:
                    continue

                summary = (
                    f"Pipeline: {pipeline_tag} | "
                    f"Likes: {likes} | Downloads: {downloads} | "
                    f"Tags: {', '.join(tags[:5])}"
                )

                items.append(RawItem(
                    source="huggingface",
                    title=model_id,
                    summary=summary[:300],
                    url=f"https://huggingface.co/{model_id}",
                    published_at=datetime.now(),
                    tags=["huggingface", pipeline_tag] if pipeline_tag else ["huggingface"],
                ))

        except Exception as e:
            _log.error("HuggingFace 采集失败: %s", e)

        _log.info("HuggingFace 采集完成，共 %d 条", len(items))
        return items
