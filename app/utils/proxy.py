"""
代理配置工具模块

提供统一的代理配置管理和请求封装，解决 GitHub/HuggingFace 等国外服务的连接问题。
"""

import os
import requests
from typing import Optional, Dict, Any
from functools import wraps

from app.config.settings import HTTP_PROXY, HTTPS_PROXY, NO_PROXY, REQUEST_TIMEOUT
from app.utils.logger import get_logger

_log = get_logger("proxy")


class ProxyManager:
    """代理管理器"""
    
    def __init__(self):
        self.http_proxy = HTTP_PROXY
        self.https_proxy = HTTPS_PROXY
        self.no_proxy = self._parse_no_proxy(NO_PROXY)
        self.enabled = bool(self.http_proxy or self.https_proxy)
        
        if self.enabled:
            _log.info("代理已启用: HTTP=%s, HTTPS=%s", 
                     self.http_proxy or "None", 
                     self.https_proxy or "None")
    
    def _parse_no_proxy(self, no_proxy_str: str) -> list:
        """解析 NO_PROXY 环境变量"""
        if not no_proxy_str:
            return ["localhost", "127.0.0.1"]
        return [host.strip() for host in no_proxy_str.split(",")]
    
    def should_use_proxy(self, url: str) -> bool:
        """判断是否应该对指定 URL 使用代理"""
        if not self.enabled:
            return False
        
        # 检查是否在 NO_PROXY 列表中
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or ""
        
        for no_proxy_host in self.no_proxy:
            if no_proxy_host in hostname:
                return False
        
        return True
    
    def get_proxies(self, url: str) -> Optional[Dict[str, str]]:
        """获取指定 URL 的代理配置"""
        if not self.should_use_proxy(url):
            return None
        
        proxies = {}
        if self.http_proxy:
            proxies["http"] = self.http_proxy
        if self.https_proxy:
            proxies["https"] = self.https_proxy
        
        return proxies if proxies else None


# 全局代理管理器实例
_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    """获取代理管理器实例（单例）"""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


def requests_with_proxy(url: str, method: str = "get", **kwargs) -> requests.Response:
    """
    带代理支持的 HTTP 请求
    
    自动根据配置添加代理，支持重试机制。
    
    Args:
        url: 请求 URL
        method: HTTP 方法 (get/post/put/delete)
        **kwargs: 传递给 requests 的其他参数
    
    Returns:
        Response 对象
    
    Raises:
        requests.RequestException: 请求失败
    """
    proxy_manager = get_proxy_manager()
    proxies = proxy_manager.get_proxies(url)
    
    # 设置超时
    timeout = kwargs.pop("timeout", REQUEST_TIMEOUT)
    
    # 合并代理配置
    if proxies:
        kwargs["proxies"] = proxies
        _log.debug("使用代理访问 %s: %s", url, proxies)
    
    # 执行请求
    request_func = getattr(requests, method.lower())
    response = request_func(url, timeout=timeout, **kwargs)
    response.raise_for_status()
    
    return response


def with_proxy_retry(max_retries: int = 3, backoff_factor: float = 1.0):
    """
    装饰器：为函数添加代理和重试支持
    
    适用于需要 HTTP 请求的采集器函数。
    
    Example:
        @with_proxy_retry(max_retries=3)
        def fetch_github_trending():
            return requests_with_proxy("https://github.com/trending").text
    """
    from functools import wraps
    import time
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    wait_time = backoff_factor * (2 ** attempt)
                    _log.warning("%s 第 %d/%d 次尝试失败: %s，%.1f 秒后重试",
                               func.__name__, attempt + 1, max_retries, e, wait_time)
                    time.sleep(wait_time)
            
            raise last_exception
        
        return wrapper
    return decorator


# 便捷函数：快速测试代理配置
def test_proxy_config():
    """测试代理配置是否正常工作"""
    print("=" * 60)
    print("代理配置测试")
    print("=" * 60)
    
    proxy_manager = get_proxy_manager()
    
    print(f"\n代理配置:")
    print(f"  HTTP 代理: {proxy_manager.http_proxy or '未设置'}")
    print(f"  HTTPS 代理: {proxy_manager.https_proxy or '未设置'}")
    print(f"  NO_PROXY: {', '.join(proxy_manager.no_proxy)}")
    print(f"  代理状态: {'已启用' if proxy_manager.enabled else '未启用'}")
    
    # 测试连接
    test_urls = [
        ("百度", "https://www.baidu.com"),
        ("GitHub", "https://api.github.com"),
        ("HuggingFace", "https://huggingface.co/api/models"),
    ]
    
    print(f"\n连接测试:")
    for name, url in test_urls:
        try:
            use_proxy = proxy_manager.should_use_proxy(url)
            response = requests_with_proxy(url, timeout=10)
            print(f"  ✅ {name}: 成功 (HTTP {response.status_code}, 代理: {use_proxy})")
        except Exception as e:
            print(f"  ❌ {name}: 失败 ({str(e)[:50]})")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_proxy_config()
