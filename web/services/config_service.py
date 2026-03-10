"""配置管理服务 - DB + .env 双向同步"""

import os
from pathlib import Path
from typing import Optional

from dotenv import set_key, dotenv_values

from web.extensions import db
from web.models.system_config import SystemConfig

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"

# 配置项定义：category → [(key, value_type, is_secret, description, default)]
CONFIG_DEFINITIONS = {
    "llm": [
        ("LLM_PROVIDER", "string", False, "LLM 提供商 (dmxapi/ollama)", "dmxapi"),
        ("DMXAPI_BASE_URL", "string", False, "DMXAPI 接口地址", "https://api.dmxapi.com/v1"),
        ("DMXAPI_API_KEY", "string", True, "DMXAPI API 密钥", ""),
        ("LLM_MODEL", "string", False, "LLM 模型名称", "gpt-4o"),
        ("OLLAMA_BASE_URL", "string", False, "Ollama 本地地址", "http://localhost:11434"),
        ("OLLAMA_MODEL", "string", False, "Ollama 模型名称", "glm-5:cloud"),
    ],
    "image": [
        ("IMAGE_PROVIDER", "string", False, "图片提供商 (flux/v3)", "v3"),
        ("IMAGE_MODEL", "string", False, "图片模型", "flux"),
        ("IDEOGRAM_API_KEY", "string", True, "Ideogram V3 API 密钥", ""),
        ("IDEOGRAM_API_URL", "string", False, "Ideogram V3 接口地址", "https://aihubmix.com/api/IdeogramAI/ideogram/generate"),
    ],
    "wechat": [
        ("WECHAT_APP_ID", "string", True, "微信公众号 AppID", ""),
        ("WECHAT_APP_SECRET", "string", True, "微信公众号 AppSecret", ""),
    ],
    "collector": [
        ("ARXIV_MAX_RESULTS", "int", False, "ArXiv 最大搜索结果数", "30"),
        ("HF_MODELS_LIMIT", "int", False, "HuggingFace 模型数量限制", "20"),
        ("TAVILY_API_KEY", "string", True, "Tavily 搜索 API 密钥", ""),
        ("TAVILY_API_URL", "string", False, "Tavily 搜索 API 地址", "https://api.tavily.com"),
    ],
    "article": [
        ("ARTICLE_MIN_WORDS", "int", False, "文章最小字数", "3000"),
        ("ARTICLE_MAX_WORDS", "int", False, "文章最大字数", "4000"),
        ("OUTPUT_BASE_DIR", "string", False, "输出根目录", r"D:\公众号"),
    ],
    "proxy": [
        ("HTTP_PROXY", "string", False, "HTTP 代理地址", ""),
        ("HTTPS_PROXY", "string", False, "HTTPS 代理地址", ""),
        ("NO_PROXY", "string", False, "不使用代理的地址", "localhost,127.0.0.1"),
        ("REQUEST_TIMEOUT", "int", False, "请求超时秒数", "30"),
        ("REQUEST_MAX_RETRIES", "int", False, "最大重试次数", "3"),
    ],
}


def init_configs_from_env():
    """从 .env 文件初始化数据库配置"""
    env_values = dotenv_values(_env_path) if _env_path.exists() else {}

    for category, items in CONFIG_DEFINITIONS.items():
        for key, value_type, is_secret, description, default in items:
            existing = SystemConfig.query.filter_by(category=category, key=key).first()
            if existing is None:
                value = env_values.get(key, os.getenv(key, default))
                config = SystemConfig(
                    category=category,
                    key=key,
                    value=value or default,
                    value_type=value_type,
                    is_secret=is_secret,
                    description=description,
                )
                db.session.add(config)
    db.session.commit()


def get_all_configs(mask_secret: bool = True) -> dict:
    """获取所有配置 (按 category 分组)"""
    # 确保配置已初始化
    total = SystemConfig.query.count()
    if total == 0:
        init_configs_from_env()

    configs = SystemConfig.query.order_by(SystemConfig.category, SystemConfig.id).all()
    result = {}
    for c in configs:
        if c.category not in result:
            result[c.category] = []
        result[c.category].append(c.to_dict(mask_secret=mask_secret))
    return result


def get_category_configs(category: str, mask_secret: bool = True) -> Optional[list]:
    """获取某类别的所有配置"""
    if category not in CONFIG_DEFINITIONS:
        return None

    total = SystemConfig.query.count()
    if total == 0:
        init_configs_from_env()

    configs = SystemConfig.query.filter_by(category=category).order_by(SystemConfig.id).all()
    return [c.to_dict(mask_secret=mask_secret) for c in configs]


def update_category_configs(category: str, updates: dict) -> bool:
    """批量更新某类别的配置"""
    if category not in CONFIG_DEFINITIONS:
        return False

    for key, value in updates.items():
        config = SystemConfig.query.filter_by(category=category, key=key).first()
        if config:
            config.value = str(value)
            # 同步写回 .env
            if _env_path.exists():
                set_key(str(_env_path), key, str(value))

    db.session.commit()

    # 尝试热更新 settings 模块
    _reload_settings()
    return True


def _reload_settings():
    """尝试热更新 app.config.settings 模块"""
    try:
        import importlib
        import app.config.settings as settings_module
        importlib.reload(settings_module)
    except Exception:
        pass  # 热更新失败不影响主流程
