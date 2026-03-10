"""内容管理服务 - 读写文件存储中的文章数据"""

import json
import re
import shutil
from pathlib import Path
from typing import Optional

from app.config.settings import OUTPUT_BASE_DIR


def _validate_date(date_str: str) -> bool:
    """验证日期格式: 6位数字 YYMMDD"""
    return bool(re.match(r"^\d{6}$", date_str))


def _safe_path(date_str: str, subdir: str = None) -> Optional[Path]:
    """安全地构建路径，防止路径穿越"""
    if not _validate_date(date_str):
        return None
    base = OUTPUT_BASE_DIR / date_str
    if subdir:
        base = base / subdir
    resolved = base.resolve()
    if not str(resolved).startswith(str(OUTPUT_BASE_DIR.resolve())):
        return None
    return resolved


def list_article_dates(page: int = 1, page_size: int = 20) -> dict:
    """列出所有文章日期目录"""
    base = OUTPUT_BASE_DIR
    dirs = []
    if base.exists():
        for d in sorted(base.iterdir(), reverse=True):
            if d.is_dir() and re.match(r"^\d{6}$", d.name):
                dirs.append(d.name)

    total = len(dirs)
    start = (page - 1) * page_size
    end = start + page_size
    page_dirs = dirs[start:end]

    items = []
    for date_str in page_dirs:
        info = get_article_summary(date_str)
        if info:
            items.append(info)

    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_article_summary(date_str: str) -> Optional[dict]:
    """获取某日文章摘要信息"""
    day_dir = _safe_path(date_str)
    if not day_dir or not day_dir.exists():
        return None

    # 格式化日期
    try:
        formatted = f"20{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}"
    except (IndexError, ValueError):
        formatted = date_str

    article_md = day_dir / "article.md"
    title = ""
    if article_md.exists():
        with open(article_md, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            title = first_line.lstrip("# ").strip()

    # 统计图片
    images = [f.name for f in day_dir.glob("*.png")]

    # 检查深度分析
    deep_dir = day_dir / "深度分析"
    has_deep = deep_dir.exists() and (deep_dir / "article.md").exists()

    # 运行报告
    report_file = day_dir / "run_report.json"
    report = None
    if report_file.exists():
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                report = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # 采集/筛选数量
    raw_count = 0
    raw_file = day_dir / "raw_data.json"
    if raw_file.exists():
        try:
            with open(raw_file, "r", encoding="utf-8") as f:
                raw_count = len(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass

    selected_count = 0
    sel_file = day_dir / "selected_data.json"
    if sel_file.exists():
        try:
            with open(sel_file, "r", encoding="utf-8") as f:
                selected_count = len(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "date": date_str,
        "date_formatted": formatted,
        "has_article": article_md.exists(),
        "has_deep_analysis": has_deep,
        "article_title": title,
        "images_count": len(images),
        "raw_data_count": raw_count,
        "selected_count": selected_count,
        "task_status": report.get("status") if report else None,
        "duration_seconds": report.get("duration_seconds") if report else None,
    }


def get_article_detail(date_str: str) -> Optional[dict]:
    """获取文章完整详情"""
    day_dir = _safe_path(date_str)
    if not day_dir or not day_dir.exists():
        return None

    result = get_article_summary(date_str) or {}

    # 读取 Markdown
    md_path = day_dir / "article.md"
    result["content_markdown"] = ""
    if md_path.exists():
        with open(md_path, "r", encoding="utf-8") as f:
            result["content_markdown"] = f.read()

    # 读取 HTML
    html_path = day_dir / "article.html"
    result["content_html"] = ""
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            result["content_html"] = f.read()

    # 图片列表
    result["images"] = sorted(
        [f.name for f in day_dir.glob("*.png")]
    )

    return result


def get_json_data(date_str: str, filename: str) -> Optional[list | dict]:
    """读取日期目录下的 JSON 数据文件"""
    allowed = {"raw_data.json", "selected_data.json", "run_report.json"}
    if filename not in allowed:
        return None

    day_dir = _safe_path(date_str)
    if not day_dir:
        return None

    file_path = day_dir / filename
    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def update_article(date_str: str, content_markdown: str) -> bool:
    """更新文章内容"""
    day_dir = _safe_path(date_str)
    if not day_dir or not day_dir.exists():
        return False

    # 保存 Markdown
    md_path = day_dir / "article.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content_markdown)

    # 简单转换为 HTML
    html_path = day_dir / "article.html"
    html_content = _markdown_to_simple_html(content_markdown)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return True


def delete_article(date_str: str) -> bool:
    """删除某日文章目录"""
    day_dir = _safe_path(date_str)
    if not day_dir or not day_dir.exists():
        return False
    shutil.rmtree(day_dir)
    return True


def get_image_path(date_str: str, filename: str) -> Optional[Path]:
    """获取图片文件路径"""
    if not re.match(r"^[\w\-\.]+\.png$", filename):
        return None

    day_dir = _safe_path(date_str)
    if not day_dir:
        return None

    file_path = day_dir / filename
    resolved = file_path.resolve()
    if not str(resolved).startswith(str(OUTPUT_BASE_DIR.resolve())):
        return None

    if file_path.exists():
        return file_path
    return None


def get_deep_image_path(date_str: str, filename: str) -> Optional[Path]:
    """获取深度分析图片文件路径"""
    if not re.match(r"^[\w\-\.]+\.png$", filename):
        return None

    day_dir = _safe_path(date_str, "深度分析")
    if not day_dir:
        return None

    file_path = day_dir / filename
    resolved = file_path.resolve()
    if not str(resolved).startswith(str(OUTPUT_BASE_DIR.resolve())):
        return None

    if file_path.exists():
        return file_path
    return None


def list_deep_analysis(page: int = 1, page_size: int = 20) -> dict:
    """列出所有深度分析文章"""
    base = OUTPUT_BASE_DIR
    items = []

    if base.exists():
        for d in sorted(base.iterdir(), reverse=True):
            if d.is_dir() and re.match(r"^\d{6}$", d.name):
                deep_dir = d / "深度分析"
                md_file = deep_dir / "article.md"
                if deep_dir.exists() and md_file.exists():
                    title = ""
                    with open(md_file, "r", encoding="utf-8") as f:
                        first_line = f.readline().strip()
                        title = first_line.lstrip("# ").strip()

                    report = None
                    report_file = deep_dir / "run_report.json"
                    if report_file.exists():
                        try:
                            with open(report_file, "r", encoding="utf-8") as f:
                                report = json.load(f)
                        except (json.JSONDecodeError, OSError):
                            pass

                    try:
                        formatted = f"20{d.name[:2]}-{d.name[2:4]}-{d.name[4:6]}"
                    except (IndexError, ValueError):
                        formatted = d.name

                    images = [f.name for f in deep_dir.glob("*.png")]

                    items.append({
                        "date": d.name,
                        "date_formatted": formatted,
                        "title": title,
                        "images_count": len(images),
                        "status": report.get("status") if report else None,
                    })

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {"items": items[start:end], "total": total, "page": page, "page_size": page_size}


def get_deep_analysis_detail(date_str: str) -> Optional[dict]:
    """获取深度分析文章详情"""
    deep_dir = _safe_path(date_str, "深度分析")
    if not deep_dir or not deep_dir.exists():
        return None

    md_path = deep_dir / "article.md"
    html_path = deep_dir / "article.html"
    report_file = deep_dir / "run_report.json"

    result = {"date": date_str}

    if md_path.exists():
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            result["content_markdown"] = content
            first_line = content.split("\n", 1)[0]
            result["title"] = first_line.lstrip("# ").strip()
    else:
        return None

    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            result["content_html"] = f.read()

    result["images"] = sorted([f.name for f in deep_dir.glob("*.png")])

    if report_file.exists():
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                result["report"] = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    return result


def _markdown_to_simple_html(md_text: str) -> str:
    """简单的 Markdown → HTML 转换"""
    lines = md_text.split("\n")
    html_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            html_lines.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("### "):
            html_lines.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("!["):
            # 图片 ![alt](src)
            match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
            if match:
                alt, src = match.group(1), match.group(2)
                html_lines.append(f'<p><img src="{src}" alt="{alt}" style="max-width:100%;" /></p>')
        elif stripped:
            html_lines.append(f"<p>{stripped}</p>")
    return "\n".join(html_lines)
