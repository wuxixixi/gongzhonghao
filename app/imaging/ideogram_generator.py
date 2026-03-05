"""
Ideogram V3 图片生成器
使用 aihubmix API 生成高质量图片
文档: https://docs.aihubmix.com/cn/api/IdeogramAI
"""

import json
import base64
from typing import List, Optional
from pathlib import Path

import requests
from PIL import Image
from io import BytesIO

from openai import OpenAI

from app.config.settings import IDEOGRAM_API_KEY, IDEOGRAM_API_URL
from app.utils.logger import get_logger

_log = get_logger("ideogram_generator")


class IdeogramGenerator:
    """Ideogram V3 图片生成器 - 使用 OpenAI 兼容 API"""

    def __init__(self):
        self.api_key = IDEOGRAM_API_KEY
        self.api_url = IDEOGRAM_API_URL

        # 使用 OpenAI 客户端
        self.client = OpenAI(
            base_url="https://aihubmix.com/api/v1",
            api_key=self.api_key,
        )

    def generate_cover(self, prompt: str, save_path: str) -> bool:
        """生成封面图"""
        _log.info("生成封面图: %s", prompt[:50])
        return self._generate_image(
            prompt=prompt,
            save_path=save_path,
            size="1792x1024"  # 16:9 宽屏
        )

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

            if self._generate_image(
                prompt=prompt,
                save_path=save_path,
                size="1024x1024"  # 正方形
            ):
                saved_paths.append(save_path)

        return saved_paths

    def _generate_image(self, prompt: str, save_path: str, size: str) -> bool:
        """调用 Ideogram V3 API 生成图片"""
        try:
            _log.info("调用 Ideogram API: model=ideogram-v3, size=%s", size)

            # 使用 OpenAI 兼容的 images.generate API
            response = self.client.images.generate(
                model="ideogram-v3",
                prompt=prompt,
                size=size,
                n=1,
            )

            _log.debug("API 响应: %s", response)

            # 获取图片 URL
            image_url = response.data[0].url
            if not image_url:
                _log.error("未返回图片 URL")
                return False

            # 下载图片
            _log.info("下载图片: %s", image_url[:80])
            img_response = requests.get(image_url, timeout=60)
            img_response.raise_for_status()

            # 保存图片
            img = Image.open(BytesIO(img_response.content))
            img.save(save_path, "PNG")

            _log.info("图片已保存: %s", save_path)
            return True

        except Exception as e:
            _log.error("Ideogram 图片生成失败: %s", e)
            return False

    def generate_all(
        self,
        cover_prompt: str,
        image_prompts: List[str],
        output_dir: str
    ) -> dict:
        """生成所有图片（封面 + 配图）"""
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

        _log.info(
            "图片生成完成: 封面 %s, 配图 %d 张",
            "成功" if result["cover"] else "失败",
            len(result["images"])
        )

        return result
