from typing import Optional

from publisher.wechat_client import WeChatClient
from publisher.media_uploader import MediaUploader
from processors.writer import ArticleResult
from utils.logger import get_logger

_log = get_logger("draft_creator")


class DraftCreator:
    """微信草稿创建器"""

    def __init__(self, client: WeChatClient = None):
        self.client = client or WeChatClient()
        self.uploader = MediaUploader(self.client)

    def create_draft(
        self,
        article: ArticleResult,
        cover_image_path: Optional[str] = None,
        inline_images: Optional[list[str]] = None,
    ) -> str:
        """创建草稿，返回 media_id"""
        _log.info("创建草稿: %s", article.title)

        # 上传封面图
        thumb_media_id = ""
        if cover_image_path:
            try:
                thumb_media_id = self.uploader.upload_image(cover_image_path)
            except Exception as e:
                _log.warning("封面上传失败: %s", e)

        # 处理内嵌图片
        content = article.content_html
        if inline_images:
            content = self._embed_images(content, inline_images)

        # 构建草稿数据
        articles_data = {
            "articles": [
                {
                    "title": article.title,
                    "author": "AI日报",
                    "digest": article.digest[:120] if article.digest else "",
                    "content": content,
                    "content_source_url": "",
                    "thumb_media_id": thumb_media_id,
                    "need_open_comment": 0,
                    "only_fans_can_comment": 0,
                }
            ]
        }

        # 调用 API
        result = self.client.request("POST", "/draft/add", json=articles_data)
        media_id = result.get("media_id", "")

        _log.info("草稿创建成功，media_id: %s", media_id)
        return media_id

    def _embed_images(self, content: str, image_paths: list[str]) -> str:
        """将图片嵌入文章内容"""
        for i, path in enumerate(image_paths[:3], start=1):
            # 替换 Markdown 格式的图片占位符
            placeholder = f"image_{i}.png"
            try:
                media_id = self.uploader.upload_image(path)
                # 微信图文中的图片需要使用特殊格式
                img_tag = f'<img src="https://mmbiz.qpic.cn/mmbiz_png/{media_id}/0" alt="配图{i}" style="max-width:100%">'
                content = content.replace(f'img src="{placeholder}"', f'img src="https://mmbiz.qpic.cn/mmbiz_png/{media_id}/0"')
                content = content.replace(f"({placeholder})", f'(https://mmbiz.qpic.cn/mmbiz_png/{media_id}/0)')
            except Exception as e:
                _log.warning("内嵌图片 %d 上传失败: %s", i, e)

        return content
