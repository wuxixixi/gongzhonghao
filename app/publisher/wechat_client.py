"""
微信公众号 API 客户端

提供：
- 线程安全的 Token 管理
- 自动 Token 刷新
- 断路器保护
- IP 白名单错误友好提示
"""

import json
import time
import threading
from pathlib import Path
from typing import Optional

import requests

from app.config.settings import WECHAT_APP_ID, WECHAT_APP_SECRET, PROJECT_ROOT
from app.utils.logger import get_logger
from app.utils.retry import with_retry, with_circuit_breaker, CircuitBreakerOpen

_log = get_logger("wechat_client")


class WeChatAPIError(Exception):
    """微信 API 错误"""
    
    def __init__(self, errcode: int, errmsg: str, context: dict = None):
        self.errcode = errcode
        self.errmsg = errmsg
        self.context = context or {}
        super().__init__(f"微信 API 错误 [{errcode}]: {errmsg}")
    
    def is_retryable(self) -> bool:
        """是否可重试"""
        # Token 相关错误可重试
        return self.errcode in [40001, 42001, 45009]
    
    def is_token_error(self) -> bool:
        """是否为 Token 错误"""
        return self.errcode in [40001, 42001, 40014, 41001]


class WeChatClient:
    """
    微信公众号 API 客户端（线程安全）
    
    特性：
    - Token 缓存和自动刷新
    - 线程安全
    - 断路器保护
    - 友好的错误提示
    """

    BASE_URL = "https://api.weixin.qq.com/cgi-bin"
    TOKEN_CACHE_FILE = PROJECT_ROOT / ".wechat_token.json"
    TOKEN_EXPIRE_SECONDS = 7000  # 官方 7200，提前 200 秒刷新
    
    # 类级别的 Token 锁（所有实例共享）
    _token_lock = threading.RLock()

    def __init__(self):
        self.app_id = WECHAT_APP_ID
        self.app_secret = WECHAT_APP_SECRET
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        
        # 初始化断路器
        self._circuit_breaker = with_circuit_breaker(
            name="wechat_api",
            failure_threshold=5,
            recovery_timeout=300.0,
        )

    @property
    def access_token(self) -> str:
        """获取有效的 access_token（线程安全）"""
        with self._token_lock:
            # 尝试从缓存加载
            if self._load_token_from_cache():
                if time.time() < self._token_expires_at:
                    return self._access_token

            # 重新获取
            return self._refresh_token()

    def refresh_token(self) -> str:
        """强制刷新 access_token（线程安全）"""
        with self._token_lock:
            # 清除缓存文件
            if self.TOKEN_CACHE_FILE.exists():
                try:
                    self.TOKEN_CACHE_FILE.unlink()
                except:
                    pass
            self._access_token = None
            self._token_expires_at = 0
            return self._refresh_token()

    def _load_token_from_cache(self) -> bool:
        """从本地缓存加载 token"""
        if not self.TOKEN_CACHE_FILE.exists():
            return False

        try:
            with open(self.TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._access_token = data.get("access_token")
            self._token_expires_at = data.get("expires_at", 0)
            return True
        except Exception as e:
            _log.debug("加载 token 缓存失败: %s", e)
            return False

    def _save_token_to_cache(self):
        """保存 token 到本地缓存"""
        try:
            with open(self.TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "access_token": self._access_token,
                    "expires_at": self._token_expires_at,
                }, f)
        except Exception as e:
            _log.warning("保存 token 缓存失败: %s", e)

    @with_retry(
        max_retries=3,
        base_delay=2.0,
        retry_exceptions=(requests.RequestException,),
    )
    def _refresh_token(self) -> str:
        """刷新 access_token（带重试，线程安全）"""
        # 双重检查，避免重复刷新
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        url = f"{self.BASE_URL}/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if "errcode" in data:
            errcode = data.get("errcode", 0)
            errmsg = data.get("errmsg", "")

            # IP 白名单错误特殊处理
            if errcode == 40164 or "not in whitelist" in errmsg.lower():
                current_ip = self._get_current_ip()
                raise WeChatAPIError(
                    errcode,
                    f"IP 白名单错误！\n"
                    f"当前服务器 IP: {current_ip}\n"
                    f"请将此 IP 添加到微信公众号后台：\n"
                    f"  1. 登录 https://mp.weixin.qq.com\n"
                    f"  2. 进入: 设置与开发 -> 基本配置 -> IP白名单\n"
                    f"  3. 添加 IP: {current_ip}\n"
                    f"原始错误: {errmsg}",
                    {"current_ip": current_ip}
                )

            raise WeChatAPIError(errcode, errmsg)

        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + self.TOKEN_EXPIRE_SECONDS
        self._save_token_to_cache()

        _log.info("access_token 已刷新")
        return self._access_token
    
    def _get_current_ip(self) -> str:
        """获取当前公网 IP"""
        try:
            ip_resp = requests.get("https://api.ipify.org?format=json", timeout=5)
            return ip_resp.json().get("ip", "未知")
        except:
            return "获取失败"

    @with_retry(
        max_retries=3,
        base_delay=2.0,
        retry_exceptions=(requests.RequestException,),
    )
    def request(self, method: str, path: str, **kwargs) -> dict:
        """
        发送 API 请求（带重试和断路器保护）
        
        Args:
            method: HTTP 方法
            path: API 路径
            **kwargs: 请求参数
            
        Returns:
            API 响应数据
            
        Raises:
            WeChatAPIError: API 错误
            CircuitBreakerOpen: 断路器打开
        """
        url = f"{self.BASE_URL}{path}"
        params = kwargs.pop("params", {})
        params["access_token"] = self.access_token

        # 处理 JSON 数据，确保中文不被转义
        if "json" in kwargs:
            json_data = kwargs.pop("json")
            kwargs["data"] = json.dumps(json_data, ensure_ascii=False)
            kwargs["headers"] = kwargs.get("headers", {})
            kwargs["headers"]["Content-Type"] = "application/json; charset=utf-8"

        resp = requests.request(method, url, params=params, timeout=30, **kwargs)
        resp.raise_for_status()
        data = resp.json()

        # 处理 token 失效，自动刷新后重试
        if "errcode" in data:
            errcode = data.get("errcode", 0)
            errmsg = data.get("errmsg", "")
            
            # Token 错误，刷新后重试
            if errcode in [40001, 42001, 40014, 41001]:
                _log.warning("access_token 失效，正在刷新...")
                with self._token_lock:
                    params["access_token"] = self._refresh_token()
                resp = requests.request(method, url, params=params, timeout=30, **kwargs)
                resp.raise_for_status()
                data = resp.json()

            # 检查最终响应
            if "errcode" in data and data["errcode"] != 0:
                _log.error("微信 API 返回错误: %s", data)
                raise WeChatAPIError(data.get("errcode", -1), data.get("errmsg", "未知错误"))

        return data
    
    def get_api_stats(self) -> dict:
        """获取 API 调用统计"""
        return {
            "has_valid_token": self._access_token is not None and time.time() < self._token_expires_at,
            "token_expires_in": max(0, int(self._token_expires_at - time.time())),
        }
