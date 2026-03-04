from pathlib import Path

from publisher.wechat_client import WeChatClient
from utils.logger import get_logger
from utils.retry import retry

_log = get_logger("media_uploader")


class MediaUploader:
    """微信素材上传器"""

    def __init__(self, client: WeChatClient = None):
        self.client = client or WeChatClient()

    @retry(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def upload_image(self, image_path: str, permanent: bool = True) -> str:
        """上传图片素材，返回 media_id"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")

        _log.info("上传图片: %s", image_path)

        # 选择接口：永久素材 vs 临时素材
        if permanent:
            url = "/material/add_material"
        else:
            url = "/media/upload"

        with open(path, "rb") as f:
            files = {
                "media": (path.name, f, "image/png"),
            }
            data = {"type": "image"}

            result = self.client.request("POST", url, files=files, data=data)

        media_id = result.get("media_id") or result.get("media_id", "")
        _log.info("图片上传成功，media_id: %s", media_id)
        return media_id

    def upload_images(self, image_paths: list[str]) -> dict[str, str]:
        """批量上传图片"""
        result = {}
        for path in image_paths:
            try:
                media_id = self.upload_image(path)
                result[path] = media_id
            except Exception as e:
                _log.warning("图片上传失败 %s: %s", path, e)
                result[path] = None
        return result
