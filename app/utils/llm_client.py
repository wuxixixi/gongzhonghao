"""
统一 LLM 客户端管理器

提供全局单例 LLM 客户端，避免重复创建连接。
支持 DMXAPI 和 Ollama 两种提供商。
"""

import threading
from typing import Optional, Tuple, Callable, Any
from dataclasses import dataclass
from enum import Enum

from openai import OpenAI

from app.config.settings import (
    DMXAPI_BASE_URL, DMXAPI_API_KEY, LLM_MODEL,
    LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL,
)
from app.utils.logger import get_logger
from app.utils.retry import with_retry, with_circuit_breaker, CircuitBreakerOpen

_log = get_logger("llm_client")


class LLMProvider(Enum):
    """LLM 提供商"""
    DMXAPI = "dmxapi"
    OLLAMA = "ollama"


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: LLMProvider
    model: str
    base_url: str
    api_key: str

    @classmethod
    def from_settings(cls) -> "LLMConfig":
        """从配置文件加载"""
        if LLM_PROVIDER == "ollama":
            return cls(
                provider=LLMProvider.OLLAMA,
                model=OLLAMA_MODEL,
                base_url=f"{OLLAMA_BASE_URL}/v1",
                api_key="ollama",
            )
        else:
            return cls(
                provider=LLMProvider.DMXAPI,
                model=LLM_MODEL,
                base_url=DMXAPI_BASE_URL,
                api_key=DMXAPI_API_KEY,
            )


class LLMClientManager:
    """
    统一 LLM 客户端管理器（线程安全单例）
    
    使用方法：
        from app.utils.llm_client import llm_client
        
        # 简单调用
        response = llm_client.chat(messages)
        
        # 带重试和断路器
        response = llm_client.chat_with_retry(messages)
    """
    
    _instance: Optional["LLMClientManager"] = None
    _lock = threading.RLock()
    
    def __new__(cls) -> "LLMClientManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            self._config = LLMConfig.from_settings()
            self._client = self._create_client()
            self._call_count = 0
            self._error_count = 0
            self._initialized = True
            
            _log.info(
                "LLM 客户端初始化完成: provider=%s, model=%s",
                self._config.provider.value,
                self._config.model
            )
    
    def _create_client(self) -> OpenAI:
        """创建 OpenAI 客户端"""
        return OpenAI(
            base_url=self._config.base_url,
            api_key=self._config.api_key,
        )
    
    @property
    def client(self) -> OpenAI:
        """获取底层 OpenAI 客户端"""
        return self._client
    
    @property
    def model(self) -> str:
        """获取当前模型名称"""
        return self._config.model
    
    @property
    def provider(self) -> LLMProvider:
        """获取当前提供商"""
        return self._config.provider
    
    def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数
            
        Returns:
            模型响应文本
        """
        self._call_count += 1
        
        try:
            response = self._client.chat.completions.create(
                model=self._config.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # 获取响应内容
            message = response.choices[0].message
            content = message.content or ""
            
            # GLM-5 等思维链模型：如果 content 为空，使用 reasoning_content
            if not content and hasattr(message, 'reasoning_content') and message.reasoning_content:
                content = message.reasoning_content
            
            return content
        except Exception as e:
            self._error_count += 1
            _log.error("LLM 调用失败: %s", e)
            raise
    
    def chat_with_retry(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        max_retries: int = 3,
        base_delay: float = 2.0,
        **kwargs
    ) -> str:
        """
        带重试的聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            max_retries: 最大重试次数
            base_delay: 基础延迟（秒）
            **kwargs: 其他参数
            
        Returns:
            模型响应文本
        """
        import time
        
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.chat(messages, temperature, max_tokens, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # 指数退避
                    _log.warning(
                        "LLM 调用失败 (尝试 %d/%d): %s, %.1f 秒后重试",
                        attempt + 1, max_retries, e, delay
                    )
                    time.sleep(delay)
        
        _log.error("LLM 调用失败 %d 次后放弃", max_retries)
        raise last_error
    
    @with_circuit_breaker(
        name="llm_chat",
        failure_threshold=5,
        recovery_timeout=60.0,
    )
    def chat_with_circuit_breaker(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        带断路器保护的聊天请求
        
        当连续失败超过阈值时，断路器打开，快速失败。
        """
        return self.chat(messages, temperature, max_tokens, **kwargs)
    
    def chat_full(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        max_retries: int = 3,
        base_delay: float = 2.0,
        **kwargs
    ) -> str:
        """
        完整功能的聊天请求（重试 + 断路器）
        
        这是推荐使用的入口方法。
        """
        import time
        
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.chat_with_circuit_breaker(
                    messages, temperature, max_tokens, **kwargs
                )
            except CircuitBreakerOpen as e:
                _log.error("断路器已打开: %s", e)
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    _log.warning(
                        "LLM 调用失败 (尝试 %d/%d): %s, %.1f 秒后重试",
                        attempt + 1, max_retries, e, delay
                    )
                    time.sleep(delay)
        
        _log.error("LLM 调用失败 %d 次后放弃", max_retries)
        raise last_error
    
    def get_stats(self) -> dict:
        """获取调用统计"""
        return {
            "total_calls": self._call_count,
            "errors": self._error_count,
            "error_rate": self._error_count / max(self._call_count, 1),
            "provider": self._config.provider.value,
            "model": self._config.model,
        }
    
    def reset_stats(self):
        """重置统计"""
        self._call_count = 0
        self._error_count = 0
    
    def get_circuit_breaker_status(self) -> str:
        """
        获取断路器状态
        
        Returns:
            断路器状态: "closed" (正常), "open" (打开), "half_open" (半开)
        """
        from app.utils.retry import get_circuit_breaker
        cb = get_circuit_breaker("llm_chat")
        if cb:
            return cb.state.value
        return "unknown"
    
    def is_circuit_breaker_open(self) -> bool:
        """
        检查断路器是否打开
        
        Returns:
            True 如果断路器打开（服务不可用）
        """
        return self.get_circuit_breaker_status() == "open"
    
    def reset_circuit_breaker(self) -> bool:
        """
        重置断路器
        
        将断路器状态重置为关闭，允许后续请求通过。
        通常在确认服务已恢复后调用。
        
        Returns:
            True 如果重置成功
        """
        from app.utils.retry import reset_circuit_breaker
        return reset_circuit_breaker("llm_chat")


# 全局单例实例
llm_client = LLMClientManager()


def get_llm_client() -> LLMClientManager:
    """获取 LLM 客户端实例"""
    return llm_client
