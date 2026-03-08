"""
重试机制和断路器模式实现

提供装饰器和上下文管理器用于：
1. 指数退避重试
2. 断路器模式（防止雪崩）
"""

import time
import random
import functools
import threading
from enum import Enum
from typing import Optional, Callable, TypeVar, Tuple, List
from datetime import datetime, timedelta

from app.utils.logger import get_logger

_log = get_logger("retry")

T = TypeVar("T")


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_exceptions: Tuple[type, ...] = (Exception,),
        abort_exceptions: Tuple[type, ...] = (),
        on_retry: Optional[Callable[[Exception, int, float], None]] = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_exceptions = retry_exceptions
        self.abort_exceptions = abort_exceptions
        self.on_retry = on_retry

    def calculate_delay(self, attempt: int) -> float:
        """计算第 attempt 次的延迟时间（指数退避）"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # 添加随机抖动，避免惊群效应
            delay *= (0.5 + random.random())

        return delay


class CircuitState(Enum):
    """断路器状态"""
    CLOSED = "closed"      # 正常，允许请求
    OPEN = "open"          # 断开，拒绝请求
    HALF_OPEN = "half_open"  # 半开，尝试恢复


class CircuitBreaker:
    """
    断路器模式实现

    防止服务故障导致的雪崩效应。
    当失败率达到阈值时，断路器打开，快速失败。
    经过冷却时间后，进入半开状态尝试恢复。
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
        expected_exception: Tuple[type, ...] = (Exception,),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = threading.RLock()

        _log.info("断路器 %s 初始化完成 (阈值=%d)", name, failure_threshold)

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            self._update_state()
            return self._state

    def _update_state(self):
        """更新断路器状态"""
        if self._state == CircuitState.OPEN:
            # 检查是否超过恢复超时时间
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    _log.info("断路器 %s 进入半开状态，尝试恢复", self.name)
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._failure_count = 0
                    self._success_count = 0

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        使用断路器包装函数调用

        Args:
            func: 要执行的函数
            *args, **kwargs: 函数参数

        Returns:
            函数执行结果

        Raises:
            CircuitBreakerOpen: 断路器打开时
            原始异常: 函数执行失败时
        """
        with self._lock:
            self._update_state()

            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpen(f"断路器 {self.name} 已打开，请求被拒绝")

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpen(
                        f"断路器 {self.name} 半开状态调用次数已达上限"
                    )
                self._half_open_calls += 1

        # 执行实际调用
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """处理成功调用"""
        with self._lock:
            self._success_count += 1

            if self._state == CircuitState.HALF_OPEN:
                # 半开状态下连续成功，关闭断路器
                if self._success_count >= self.half_open_max_calls:
                    _log.info("断路器 %s 恢复，进入关闭状态", self.name)
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._half_open_calls = 0

    def _on_failure(self):
        """处理失败调用"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == CircuitState.HALF_OPEN:
                # 半开状态下失败，重新打开
                _log.warning("断路器 %s 恢复失败，重新打开", self.name)
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
            elif self._failure_count >= self.failure_threshold:
                # 失败次数达到阈值，打开断路器
                _log.warning(
                    "断路器 %s 打开 (失败%d次)",
                    self.name, self._failure_count
                )
                self._state = CircuitState.OPEN


class CircuitBreakerOpen(Exception):
    """断路器打开异常"""
    pass


# 全局断路器注册表
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """获取指定名称的断路器"""
    return _circuit_breakers.get(name)


def reset_circuit_breaker(name: str) -> bool:
    """
    重置指定断路器
    
    Args:
        name: 断路器名称
        
    Returns:
        True 如果重置成功
    """
    cb = _circuit_breakers.get(name)
    if cb:
        with cb._lock:
            cb._state = CircuitState.CLOSED
            cb._failure_count = 0
            cb._success_count = 0
            cb._half_open_calls = 0
            cb._last_failure_time = None
        _log.info("断路器 %s 已重置", name)
        return True
    return False


def reset_all_circuit_breakers():
    """重置所有断路器"""
    for name in _circuit_breakers:
        reset_circuit_breaker(name)
    _log.info("所有断路器已重置")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        retry_exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数，参数为(异常, 尝试次数, 延迟时间)

    Example:
        @with_retry(max_retries=3, retry_exceptions=(requests.RequestException,))
        def fetch_data():
            return requests.get(url)
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_exceptions=retry_exceptions,
        on_retry=on_retry,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.retry_exceptions as e:
                    last_exception = e
                    if attempt >= config.max_retries:
                        _log.error(
                            "%s 重试%d次后仍然失败: %s",
                            func.__name__, config.max_retries, e
                        )
                        raise

                    delay = config.calculate_delay(attempt)
                    _log.warning(
                        "%s 第%d次失败: %s, %.1f秒后重试",
                        func.__name__, attempt + 1, e, delay
                    )

                    if config.on_retry:
                        try:
                            config.on_retry(e, attempt + 1, delay)
                        except:
                            pass

                    time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Tuple[type, ...] = (Exception,),
):
    """
    断路器装饰器

    Args:
        name: 断路器名称
        failure_threshold: 失败阈值
        recovery_timeout: 恢复超时（秒）
        expected_exception: 预期异常类型

    Example:
        @with_circuit_breaker(name="wechat_api", failure_threshold=3)
        def publish_to_wechat():
            # 调用微信API
            pass
    """
    # 使用全局注册表，确保同名断路器为同一实例
    if name in _circuit_breakers:
        breaker = _circuit_breakers[name]
    else:
        breaker = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
        )
        _circuit_breakers[name] = breaker

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return breaker.call(func, *args, **kwargs)
        return wrapper

    return decorator


# 预定义的常用重试配置
RETRY_FAST = RetryConfig(max_retries=3, base_delay=0.5, max_delay=5.0)
RETRY_NORMAL = RetryConfig(max_retries=3, base_delay=1.0, max_delay=60.0)
RETRY_SLOW = RetryConfig(max_retries=5, base_delay=2.0, max_delay=300.0)


# 兼容旧接口：retry 装饰器
def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[type, ...] = (Exception,),
):
    """
    兼容旧接口的 retry 装饰器

    Args:
        max_attempts: 最大重试次数
        delay: 基础延迟（秒）
        exceptions: 需要重试的异常类型
    """
    return with_retry(
        max_retries=max_attempts - 1,
        base_delay=delay,
        max_delay=delay * 10,
        retry_exceptions=exceptions,
    )
