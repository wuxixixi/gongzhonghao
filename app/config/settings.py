import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        print(f"[FATAL] 缺少必填配置项: {key}，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)
    return val


# --- LLM Provider Selection ---
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "dmxapi")  # "ollama" or "dmxapi"

# --- Ollama (Local LLM) ---
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "glm-5:cloud")

# --- DMXAPI (Cloud API) ---
DMXAPI_BASE_URL: str = _require("DMXAPI_BASE_URL")
DMXAPI_API_KEY: str = _require("DMXAPI_API_KEY")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")

# --- 图片生成 API 配置（独立于 LLM）---
# 用于 Flux/Ideogram 等图片生成服务
IMAGE_API_BASE_URL: str = os.getenv("IMAGE_API_BASE_URL", "https://www.dmxapi.cn/v1")
IMAGE_API_KEY: str = os.getenv("IMAGE_API_KEY", "")
IMAGE_MODEL: str = os.getenv("IMAGE_MODEL", "flux-2-pro")

# --- 图片生成器选择 ---
# 可选: "flux" 或 "v3" (Ideogram V3)
IMAGE_PROVIDER: str = os.getenv("IMAGE_PROVIDER", "v3").lower()

# --- Ideogram V3 (Image Generation) ---
IDEOGRAM_API_KEY: str = os.getenv("IDEOGRAM_API_KEY", "")
IDEOGRAM_API_URL: str = os.getenv("IDEOGRAM_API_URL", "https://aihubmix.com/api/IdeogramAI/ideogram/generate")

# --- 微信 ---
WECHAT_APP_ID: str = _require("WECHAT_APP_ID")
WECHAT_APP_SECRET: str = _require("WECHAT_APP_SECRET")

# --- 采集 ---
ARXIV_MAX_RESULTS: int = int(os.getenv("ARXIV_MAX_RESULTS", "30"))
HF_MODELS_LIMIT: int = int(os.getenv("HF_MODELS_LIMIT", "20"))

# --- Tavily 搜索 ---
TAVILY_API_KEY: str = _require("TAVILY_API_KEY")
TAVILY_API_URL: str = os.getenv("TAVILY_API_URL", "https://api.tavily.com")

# --- 文章 ---
ARTICLE_MIN_WORDS: int = int(os.getenv("ARTICLE_MIN_WORDS", "3000"))
ARTICLE_MAX_WORDS: int = int(os.getenv("ARTICLE_MAX_WORDS", "4000"))

# --- 存储 ---
OUTPUT_BASE_DIR: Path = Path(os.getenv("OUTPUT_BASE_DIR", r"D:\公众号"))

def get_daily_dir() -> Path:
    """返回当天的输出目录，如 D:\公众号\260304"""
    today = datetime.now().strftime("%y%m%d")
    return OUTPUT_BASE_DIR / today

# --- 项目根目录 ---
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

# --- 代理配置 ---
HTTP_PROXY: str = os.getenv("HTTP_PROXY", "")
HTTPS_PROXY: str = os.getenv("HTTPS_PROXY", "")
NO_PROXY: str = os.getenv("NO_PROXY", "localhost,127.0.0.1")

# --- 网络请求配置 ---
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
REQUEST_MAX_RETRIES: int = int(os.getenv("REQUEST_MAX_RETRIES", "3"))
