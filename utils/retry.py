import time
import functools
from utils.logger import get_logger

_log = get_logger("retry")


def retry(max_attempts: int = 3, delay: float = 2.0, exceptions=(Exception,)):
    """重试装饰器，指数退避"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts:
                        wait = delay * (2 ** (attempt - 1))
                        _log.warning(
                            "%s 第%d次失败: %s，%.1fs 后重试",
                            func.__name__, attempt, e, wait,
                        )
                        time.sleep(wait)
                    else:
                        _log.error("%s 全部%d次尝试失败: %s", func.__name__, max_attempts, e)
            raise last_exc
        return wrapper
    return decorator
