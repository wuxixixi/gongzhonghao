from typing import Optional, List

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
        inline_images: Optional[List[str]] = None,
    ) -> str:
        """
        创建草稿，返回 media_id

        Args:
            article: 文章内容
            cover_image_path: 封面图路径
            inline_images: 正文中配图路径列表

        Returns:
            草稿的 media_id
        """
        _log.info("创建草稿: %s", article.title)

        # Step 1: 上传封面图为永久素材
        thumb_media_id = ""
        if cover_image_path:
            try:
                thumb_media_id = self.uploader.upload_thumb(cover_image_path)
            except Exception as e:
                _log.warning("封面上传失败: %s", e)

        # Step 2: 处理正文中的图片
        content = article.content_html
        if inline_images:
            content = self._embed_images(content, inline_images)

        # Step 3: 构建草稿数据
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

        # Step 4: 调用 API
        result = self.client.request("POST", "/draft/add", json=articles_data)
        media_id = result.get("media_id", "")

        _log.info("草稿创建成功，media_id: %s", media_id)
        return media_id

    def _embed_images(self, content: str, image_paths: List[str]) -> str:
        """
        将图片嵌入文章内容

        使用 /media/uploadimg 接口上传图片获取 URL，
        然后替换文章中的图片占位符
        """
        for i, path in enumerate(image_paths[:3], start=1):
            placeholder = f"image_{i}.png"

            try:
                # 上传正文图片，获取 URL
                image_url = self.uploader.upload_content_image(path)

                # 替换占位符为实际 URL
                # 替换 Markdown 格式
                content = content.replace(f"({placeholder})", f"({image_url})")
                # 替换 HTML 格式
                content = content.replace(f'src="{placeholder}"', f'src="{image_url}"')
                content = content.replace(f"src='{placeholder}'", f"src='{image_url}'")

                _log.info("正文图片 %d 已嵌入", i)

            except Exception as e:
                _log.warning("正文图片 %d 上传失败: %s", i, e)

        return content
