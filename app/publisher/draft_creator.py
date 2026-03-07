"""
微信草稿创建器

提供：
- 发布前内容验证
- 图片上传和嵌入
- 草稿创建
"""

from dataclasses import dataclass
from typing import Optional, List

from app.publisher.wechat_client import WeChatClient, WeChatAPIError
from app.publisher.media_uploader import MediaUploader
from app.processors.writer import ArticleResult
from app.utils.logger import get_logger

_log = get_logger("draft_creator")


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __bool__(self) -> bool:
        return self.valid


class ArticleValidator:
    """文章内容验证器"""
    
    # 微信公众号限制
    MAX_TITLE_LENGTH = 64
    MAX_DIGEST_LENGTH = 120
    MAX_CONTENT_LENGTH = 20000  # 建议
    
    @classmethod
    def validate(cls, article: ArticleResult) -> ValidationResult:
        """
        验证文章内容是否符合微信公众号要求
        
        Args:
            article: 文章内容
            
        Returns:
            验证结果
        """
        errors = []
        warnings = []
        
        # 验证标题
        if not article.title:
            errors.append("标题为空")
        elif len(article.title) < 5:
            errors.append(f"标题过短: {len(article.title)} 字符（建议至少 5 字符）")
        elif len(article.title) > cls.MAX_TITLE_LENGTH:
            errors.append(f"标题过长: {len(article.title)} 字符（限制 {cls.MAX_TITLE_LENGTH} 字符）")
        
        # 验证摘要
        if article.digest and len(article.digest) > cls.MAX_DIGEST_LENGTH:
            errors.append(f"摘要过长: {len(article.digest)} 字符（限制 {cls.MAX_DIGEST_LENGTH} 字符）")
        
        # 验证正文
        if not article.content_html:
            errors.append("文章正文为空")
        elif len(article.content_html) > cls.MAX_CONTENT_LENGTH:
            warnings.append(f"文章较长: {len(article.content_html)} 字符（建议控制在 {cls.MAX_CONTENT_LENGTH} 字符内）")
        
        # 验证封面图提示词
        if not article.cover_prompt:
            warnings.append("封面图提示词为空，将使用默认提示词")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )


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
        skip_validation: bool = False,
    ) -> str:
        """
        创建草稿，返回 media_id

        Args:
            article: 文章内容
            cover_image_path: 封面图路径
            inline_images: 正文中配图路径列表
            skip_validation: 是否跳过验证

        Returns:
            草稿的 media_id
            
        Raises:
            ValueError: 内容验证失败
            WeChatAPIError: API 调用失败
        """
        _log.info("创建草稿: %s", article.title)
        
        # 验证文章内容
        if not skip_validation:
            validation = ArticleValidator.validate(article)
            if not validation.valid:
                raise ValueError(f"文章验证失败: {'; '.join(validation.errors)}")
            
            for warning in validation.warnings:
                _log.warning("文章验证警告: %s", warning)

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
        try:
            result = self.client.request("POST", "/draft/add", json=articles_data)
            media_id = result.get("media_id", "")
            
            _log.info("草稿创建成功，media_id: %s", media_id)
            return media_id
            
        except WeChatAPIError as e:
            _log.error("草稿创建失败: %s", e)
            raise

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
