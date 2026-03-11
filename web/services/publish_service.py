"""发布管理服务"""

import json
from datetime import datetime, timezone
from pathlib import Path

from web.extensions import db
from web.models.publication import PublicationRecord
from app.config.settings import OUTPUT_BASE_DIR


def create_draft(date_str: str, article_type: str, user_id: int) -> dict:
    """创建微信草稿"""
    if article_type == "deep_analysis":
        day_dir = OUTPUT_BASE_DIR / date_str / "深度分析"
    else:
        day_dir = OUTPUT_BASE_DIR / date_str

    html_path = day_dir / "article.html"
    md_path = day_dir / "article.md"
    cover_path = day_dir / "cover.png"

    if not html_path.exists() and not md_path.exists():
        return {"error": "文章文件不存在"}

    # 读取标题
    title = ""
    if md_path.exists():
        with open(md_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            title = first_line.lstrip("# ").strip()

    try:
        from app.publisher.wechat_client import WeChatClient
        from app.publisher.media_uploader import MediaUploader

        client = WeChatClient()
        uploader = MediaUploader(client)

        # 读取 HTML 内容
        content_html = ""
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                content_html = f.read()

        # 上传封面
        thumb_media_id = None
        if cover_path.exists():
            thumb_media_id = uploader.upload_thumb(str(cover_path))

        # 上传内文图片并替换 URL
        for img_file in sorted(day_dir.glob("image_*.png")):
            img_url = uploader.upload_content_image(str(img_file))
            if img_url:
                content_html = content_html.replace(img_file.name, img_url)

        # 创建草稿
        if thumb_media_id:
            result = client.request("POST", "/draft/add", json={
                "articles": [{
                    "title": title[:64],
                    "author": "AI 日报",
                    "digest": title[:120],
                    "content": content_html,
                    "thumb_media_id": thumb_media_id,
                    "content_source_url": "",
                    "show_cover_pic": 1,
                }]
            })
            media_id = result.get("media_id", "")
        else:
            return {"error": "封面图上传失败"}

        # 记录发布
        record = PublicationRecord(
            article_date=date_str,
            article_type=article_type,
            title=title,
            media_id=media_id,
            status="draft_created",
            published_by=user_id,
        )
        db.session.add(record)
        db.session.commit()

        return {"media_id": media_id, "title": title, "record_id": record.id}

    except Exception as e:
        return {"error": str(e)}


def list_records(page: int = 1, page_size: int = 20) -> dict:
    """发布记录列表"""
    query = PublicationRecord.query.order_by(PublicationRecord.created_at.desc())
    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [r.to_dict() for r in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_wechat_token_status() -> dict:
    """获取微信 Token 状态"""
    import time

    token_file = Path(OUTPUT_BASE_DIR).parent / ".wechat_token.json"
    # 也检查项目根目录
    if not token_file.exists():
        from app.config.settings import PROJECT_ROOT
        token_file = PROJECT_ROOT / ".wechat_token.json"

    if not token_file.exists():
        return {"status": "no_token", "has_valid_token": False}

    try:
        with open(token_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        expires_at = data.get("expires_at", 0)
        remaining = int(expires_at - time.time())
        return {
            "status": "valid" if remaining > 0 else "expired",
            "has_valid_token": remaining > 0,
            "expires_in_seconds": max(0, remaining),
        }
    except (json.JSONDecodeError, OSError):
        return {"status": "error", "has_valid_token": False}


def refresh_wechat_token() -> dict:
    """强制刷新微信 Token"""
    try:
        from app.publisher.wechat_client import WeChatClient
        client = WeChatClient()
        token = client.refresh_token()
        return {"success": True, "has_token": bool(token)}
    except Exception as e:
        return {"success": False, "error": str(e)}
