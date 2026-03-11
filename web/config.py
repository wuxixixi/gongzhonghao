"""Flask 配置类"""

import os
from datetime import timedelta
from pathlib import Path

_base_dir = Path(__file__).resolve().parent.parent


class BaseConfig:
    """基础配置"""
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "wechat-ai-admin-secret-key-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_TOKEN_LOCATION = ["headers"]

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{_base_dir / 'instance' / 'app.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"]

    # 限流默认配置
    RATELIMIT_DEFAULT = "60/minute"
    RATELIMIT_STORAGE_URI = "memory://"

    # 项目根目录
    PROJECT_ROOT = str(_base_dir)


class DevelopmentConfig(BaseConfig):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(BaseConfig):
    """生产环境配置"""
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
