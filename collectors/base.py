from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from abc import ABC, abstractmethod


@dataclass
class RawItem:
    """采集到的原始资讯条目"""
    source: str                          # "arxiv" / "news" / "github" / "huggingface"
    title: str
    summary: str                         # 200字以内摘要
    url: str
    published_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
            "tags": self.tags,
        }


class BaseCollector(ABC):
    """采集器抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """采集器名称，用于日志"""
        ...

    @abstractmethod
    def collect(self) -> List[RawItem]:
        """执行采集，返回条目列表"""
        ...
