"""监控服务 - 日志读取与系统状态"""

import os
import re
import json
import time
import platform
from pathlib import Path
from datetime import datetime

from app.config.settings import OUTPUT_BASE_DIR, PROJECT_ROOT


def get_system_status() -> dict:
    """获取系统状态总览"""
    import sys

    # 微信 Token 状态
    wechat_status = {"status": "unknown", "has_valid_token": False}
    token_file = PROJECT_ROOT / ".wechat_token.json"
    if token_file.exists():
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                token_data = json.load(f)
            expires_at = token_data.get("expires_at", 0)
            if time.time() < expires_at:
                wechat_status = {
                    "status": "healthy",
                    "has_valid_token": True,
                    "token_expires_in": int(expires_at - time.time()),
                }
            else:
                wechat_status = {"status": "expired", "has_valid_token": False}
        except (json.JSONDecodeError, OSError):
            pass

    # 存储统计
    storage_size = 0
    dir_count = 0
    if OUTPUT_BASE_DIR.exists():
        for d in OUTPUT_BASE_DIR.iterdir():
            if d.is_dir() and re.match(r"^\d{6}$", d.name):
                dir_count += 1
                for f in d.rglob("*"):
                    if f.is_file():
                        storage_size += f.stat().st_size

    # 今日摘要
    today = datetime.now().strftime("%y%m%d")
    today_dir = OUTPUT_BASE_DIR / today
    has_article = (today_dir / "article.md").exists() if today_dir.exists() else False
    has_deep = (today_dir / "深度分析" / "article.md").exists() if today_dir.exists() else False

    return {
        "system": {
            "python_version": sys.version.split()[0],
            "platform": platform.system(),
            "project_root": str(PROJECT_ROOT),
        },
        "services": {
            "wechat": wechat_status,
        },
        "storage": {
            "total_days": dir_count,
            "total_size_mb": round(storage_size / (1024 * 1024), 2),
        },
        "today": {
            "date": today,
            "has_article": has_article,
            "has_deep_analysis": has_deep,
        },
    }


def list_log_files() -> list:
    """列出所有日志文件"""
    log_dir = PROJECT_ROOT / "logs"
    if not log_dir.exists():
        return []

    files = []
    for f in sorted(log_dir.iterdir(), reverse=True):
        if f.is_file() and f.suffix == ".log":
            files.append({
                "name": f.name,
                "date": f.stem,
                "size_kb": round(f.stat().st_size / 1024, 1),
            })
    return files


def get_log_content(date: str, level: str = None, keyword: str = None,
                    offset: int = 0, limit: int = 500) -> dict:
    """获取某日日志内容"""
    log_dir = PROJECT_ROOT / "logs"

    # 尝试结构化日志
    structured_file = log_dir / f"{date}_structured.jsonl"
    if structured_file.exists():
        return _read_structured_log(structured_file, level, keyword, offset, limit)

    # 普通日志
    log_file = log_dir / f"{date}.log"
    if not log_file.exists():
        return {"lines": [], "total": 0, "offset": offset}

    return _read_plain_log(log_file, level, keyword, offset, limit)


def _read_plain_log(log_file: Path, level: str, keyword: str,
                    offset: int, limit: int) -> dict:
    """读取普通日志文件"""
    lines = []
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except OSError:
        return {"lines": [], "total": 0, "offset": offset}

    filtered = []
    for raw_line in all_lines:
        raw_line = raw_line.rstrip("\n")
        if not raw_line:
            continue
        if level and f"[{level.upper()}]" not in raw_line:
            continue
        if keyword and keyword.lower() not in raw_line.lower():
            continue
        filtered.append({"raw": raw_line})

    total = len(filtered)
    page_lines = filtered[offset:offset + limit]
    return {"lines": page_lines, "total": total, "offset": offset}


def _read_structured_log(log_file: Path, level: str, keyword: str,
                         offset: int, limit: int) -> dict:
    """读取结构化 JSON 日志"""
    lines = []
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if level and entry.get("level", "").upper() != level.upper():
                    continue
                if keyword and keyword.lower() not in json.dumps(entry, ensure_ascii=False).lower():
                    continue
                lines.append(entry)
    except OSError:
        return {"lines": [], "total": 0, "offset": offset}

    total = len(lines)
    page_lines = lines[offset:offset + limit]
    return {"lines": page_lines, "total": total, "offset": offset}


def stream_log_generator():
    """SSE 日志流生成器 - 实时追踪当日日志"""
    log_dir = PROJECT_ROOT / "logs"
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"{today}.log"

    if not log_file.exists():
        yield f"data: {json.dumps({'message': '今日日志文件不存在', 'level': 'INFO'})}\n\n"
        return

    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        # 跳到文件末尾
        f.seek(0, 2)
        while True:
            line = f.readline()
            if line:
                line = line.rstrip("\n")
                if line:
                    data = json.dumps({"raw": line}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
            else:
                time.sleep(0.5)
                # 检查是否跨天了
                new_today = datetime.now().strftime("%Y%m%d")
                if new_today != today:
                    break
