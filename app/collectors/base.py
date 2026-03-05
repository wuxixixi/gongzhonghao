from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Callable
from abc import ABC, abstractmethod
from functools import wraps

from app.utils.retry import with_retry, CircuitBreaker
from app.utils.logger import get_logger

_log = get_logger("collectors")


def collector_retry(max_retries: int = 3, base_delay: float = 2.0):
    """采集器专用的重试装饰器"""
    return with_retry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=30.0,
        retry_exceptions=(Exception,),
        on_retry=lambda exc, attempt, delay: _log.warning(
            "采集失败，第%d次重试 (%.1f秒后): %s",
            attempt, delay, exc
        ),
    )


def get_collector_circuit_breaker(name: str) -> CircuitBreaker:
    """获取采集器专用的断路器"""
    return CircuitBreaker(
        name=f"collector_{name}",
        failure_threshold=5,
        recovery_timeout=300.0,  # 5分钟后尝试恢复
        half_open_max_calls=2,
        expected_exception=(Exception,),
    )


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
