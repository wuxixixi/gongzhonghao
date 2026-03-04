import json
import time
from pathlib import Path

import requests

from config.settings import WECHAT_APP_ID, WECHAT_APP_SECRET, PROJECT_ROOT
from utils.logger import get_logger
from utils.retry import retry

_log = get_logger("wechat_client")


class WeChatClient:
    """微信公众号 API 客户端"""

    BASE_URL = "https://api.weixin.qq.com/cgi-bin"
    TOKEN_CACHE_FILE = PROJECT_ROOT / ".wechat_token.json"
    TOKEN_EXPIRE_SECONDS = 7000  # 官方 7200，提前 200 秒刷新

    def __init__(self):
        self.app_id = WECHAT_APP_ID
        self.app_secret = WECHAT_APP_SECRET
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    @property
    def access_token(self) -> str:
        """获取有效的 access_token"""
        # 尝试从缓存加载
        if self._load_token_from_cache():
            if time.time() < self._token_expires_at:
                return self._access_token

        # 重新获取
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

    @retry(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def _refresh_token(self) -> str:
        """刷新 access_token"""
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
            raise RuntimeError(f"微信 API 错误: {data.get('errmsg')}")

        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + self.TOKEN_EXPIRE_SECONDS
        self._save_token_to_cache()

        _log.info("access_token 已刷新")
        return self._access_token

    def request(self, method: str, path: str, **kwargs) -> dict:
        """发送 API 请求"""
        url = f"{self.BASE_URL}{path}"
        params = kwargs.pop("params", {})
        params["access_token"] = self.access_token

        resp = requests.request(method, url, params=params, timeout=30, **kwargs)
        resp.raise_for_status()
        data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            _log.error("微信 API 返回错误: %s", data)
            raise RuntimeError(f"微信 API 错误: {data.get('errmsg')}")

        return data
