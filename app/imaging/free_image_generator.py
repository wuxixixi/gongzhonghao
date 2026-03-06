"""
免费备用图片生成器
使用 Pollinations.ai 免费服务（无需 API Key）
"""

import os
from typing import List
import requests
from PIL import Image
from io import BytesIO
import urllib.parse

from app.utils.logger import get_logger
from app.utils.retry import with_retry

_log = get_logger("free_image_generator")

# 图片最小有效大小
MIN_IMAGE_SIZE = 1000

# Pollinations.ai 免费服务
POLLINATIONS_API_URL = "https://image.pollinations.ai/prompt/{prompt}"


class FreeImageGenerator:
    """
    免费图片生成器 - 使用 Pollinations.ai
    无需 API Key，作为最后的备用方案
    """

    MAX_SINGLE_IMAGE_RETRIES = 2

    def generate_cover(self, prompt: str, save_path: str) -> bool:
        """生成封面图"""
        _log.info("使用 Pollinations.ai 生成封面图: %s", prompt[:50])
        return self._generate_image(prompt, save_path, width=1792, height=1024)

    def generate_inline_images(
        self,
        prompts: List[str],
        save_dir: str,
        prefix: str = "image"
    ) -> List[str]:
        """生成多张配图"""
        saved_paths = []

        for i, prompt in enumerate(prompts[:3], start=1):
            save_path = f"{save_dir}/{prefix}_{i}.png"
            _log.info("生成配图 %d: %s", i, prompt[:50])

            if self._generate_image(prompt, save_path, width=1024, height=1024):
                saved_paths.append(save_path)

        return saved_paths

    @with_retry(max_retries=3, base_delay=2.0, retry_exceptions=(requests.RequestException,))
    def _generate_image(self, prompt: str, save_path: str, width: int = 1024, height: int = 1024) -> bool:
        """调用 Pollinations.ai 生成图片"""
        try:
            # 构建请求 URL
            encoded_prompt = urllib.parse.quote(prompt + ", high quality, digital art")
            url = f"{POLLINATIONS_API_URL.format(prompt=encoded_prompt)}?width={width}&height={height}&nologo=true"

            _log.info("请求 Pollinations.ai: %s", url[:100])

            # 请求图片
            response = requests.get(url, timeout=120)
            response.raise_for_status()

            # 保存图片
            img = Image.open(BytesIO(response.content))
            img.save(save_path, "PNG")

            # 验证
            if self._validate_image(save_path):
                _log.info("图片已保存: %s", save_path)
                return True
            else:
                _log.warning("图片验证失败")
                if os.path.exists(save_path):
                    os.remove(save_path)
                return False

        except Exception as e:
            _log.warning("Pollinations.ai 生成失败: %s", e)
            raise

    def _validate_image(self, image_path: str) -> bool:
        """验证图片是否有效"""
        try:
            if not os.path.exists(image_path):
                return False

            file_size = os.path.getsize(image_path)
            if file_size < MIN_IMAGE_SIZE:
                return False

            with Image.open(image_path) as img:
                img.verify()

            return True
        except Exception:
            return False

    def generate_all(
        self,
        cover_prompt: str,
        image_prompts: List[str],
        output_dir: str
    ) -> dict:
        """生成所有图片"""
        result = {
            "cover": None,
            "images": [],
        }

        # 生成封面
        cover_path = f"{output_dir}/cover.png"
        if self.generate_cover(cover_prompt, cover_path):
            result["cover"] = cover_path

        # 生成配图
        images = self.generate_inline_images(image_prompts, output_dir)
        result["images"] = images

        return result
