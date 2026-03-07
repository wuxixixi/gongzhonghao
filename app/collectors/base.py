"""
采集器基类模块

提供采集器的抽象基类和通用功能：
- 统一的错误处理
- 请求限流
- 结果验证
- 断路器保护
- 采集统计
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Callable, Any
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


# 全局断路器注册表
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_or_create_circuit_breaker(name: str) -> CircuitBreaker:
    """获取或创建断路器（单例）"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = get_collector_circuit_breaker(name)
    return _circuit_breakers[name]


@dataclass
class RawItem:
    """采集到的原始资讯条目"""
    source: str                          # "arxiv" / "news" / "github" / "huggingface"
    title: str
    summary: str                         # 200字以内摘要
    url: str
    published_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)  # 额外元数据

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
            "tags": self.tags,
            "extra": self.extra,
        }
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        验证采集项的有效性
        
        Returns:
            (是否有效, 错误信息)
        """
        if not self.title or len(self.title.strip()) < 5:
            return False, "标题过短或为空"
        if len(self.title) > 500:
            return False, "标题过长"
        if not self.summary or len(self.summary.strip()) < 20:
            return False, "摘要过短或为空"
        if not self.url:
            return False, "URL 为空"
        return True, None


@dataclass
class CollectorStats:
    """采集器统计信息"""
    name: str
    total_items: int = 0
    valid_items: int = 0
    invalid_items: int = 0
    errors: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def success_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.valid_items / self.total_items
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_items": self.total_items,
            "valid_items": self.valid_items,
            "invalid_items": self.invalid_items,
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 2),
            "success_rate": round(self.success_rate * 100, 1),
        }


class BaseCollector(ABC):
    """
    增强版采集器抽象基类
    
    提供统一的：
    - 错误处理
    - 结果验证
    - 限流控制
    - 断路器保护
    - 统计信息
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """采集器名称，用于日志"""
        ...
    
    @property
    def rate_limit_delay(self) -> float:
        """请求间隔（秒），子类可覆盖"""
        return 0.5
    
    @property
    def max_retries(self) -> int:
        """最大重试次数"""
        return 3
    
    @property
    def timeout(self) -> int:
        """请求超时（秒）"""
        return 30
    
    @property
    def min_summary_length(self) -> int:
        """最小摘要长度"""
        return 20
    
    @property
    def min_title_length(self) -> int:
        """最小标题长度"""
        return 5
    
    def __init__(self):
        self._stats = CollectorStats(name=self.name)
        self._circuit_breaker = get_or_create_circuit_breaker(self.name)
        self._last_request_time: float = 0
    
    def collect(self) -> List[RawItem]:
        """
        执行采集（带统一错误处理）
        
        子类应实现 _do_collect() 方法
        """
        self._stats = CollectorStats(name=self.name)
        self._stats.start_time = time.time()
        
        _log.info("[%s] 开始采集", self.name)
        
        try:
            # 检查断路器状态
            if self._circuit_breaker.state.value == "open":
                _log.warning("[%s] 断路器已打开，跳过采集", self.name)
                return []
            
            # 执行实际采集
            raw_items = self._do_collect()
            self._stats.total_items = len(raw_items)
            
            # 验证并过滤
            valid_items = []
            for item in raw_items:
                is_valid, error = item.validate()
                if is_valid:
                    valid_items.append(item)
                    self._stats.valid_items += 1
                else:
                    self._stats.invalid_items += 1
                    _log.debug("[%s] 过滤无效项: %s - %s", self.name, item.title[:30], error)
            
            self._stats.end_time = time.time()
            
            _log.info(
                "[%s] 采集完成: 有效 %d 条, 无效 %d 条, 耗时 %.2f 秒",
                self.name,
                self._stats.valid_items,
                self._stats.invalid_items,
                self._stats.duration_seconds
            )
            
            # 记录成功（用于断路器恢复）
            self._circuit_breaker._on_success()
            
            return valid_items
            
        except Exception as e:
            self._stats.errors.append(str(e))
            self._stats.end_time = time.time()
            
            _log.error(
                "[%s] 采集失败: %s, 耗时 %.2f 秒",
                self.name, e, self._stats.duration_seconds
            )
            
            # 记录失败（触发断路器）
            self._circuit_breaker._on_failure()
            
            return []
    
    @abstractmethod
    def _do_collect(self) -> List[RawItem]:
        """
        实际采集逻辑（子类实现）
        
        注意：此方法不应包含 try-except，由基类统一处理
        """
        ...
    
    def _rate_limit(self):
        """限流控制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()
    
    def get_stats(self) -> CollectorStats:
        """获取采集统计"""
        return self._stats
    
    def get_circuit_breaker_status(self) -> str:
        """获取断路器状态"""
        return self._circuit_breaker.state.value
