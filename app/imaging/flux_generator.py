from typing import List, Optional

from openai import OpenAI
from PIL import Image
import requests
from io import BytesIO

from app.config.settings import DMXAPI_BASE_URL, DMXAPI_API_KEY, IMAGE_MODEL
from app.utils.logger import get_logger

_log = get_logger("flux_generator")

# 风格后缀，统一追加到所有提示词
STYLE_SUFFIX = ", digital art, tech aesthetic, clean design, high quality"


class FluxGenerator:
    """Flux 图片生成器 - 通过 dmxapi 调用"""

    # 图片尺寸
    COVER_SIZE = "1792x1024"      # 封面图 (16:9)
    INLINE_SIZE = "1024x768"       # 配图 (4:3 横向)

    def __init__(self):
        self.client = OpenAI(
            base_url=DMXAPI_BASE_URL,
            api_key=DMXAPI_API_KEY,
        )

    def generate_cover(self, prompt: str, save_path: str) -> bool:
        """生成封面图"""
        full_prompt = prompt + STYLE_SUFFIX
        _log.info("生成封面图: %s", full_prompt[:50])

        return self._generate_image(full_prompt, save_path, self.COVER_SIZE)

    def generate_inline_images(
        self,
        prompts: List[str],
        save_dir: str,
        prefix: str = "image"
    ) -> List[str]:
        """生成多张配图"""
        saved_paths = []

        for i, prompt in enumerate(prompts[:3], start=1):
            full_prompt = prompt + STYLE_SUFFIX
            save_path = f"{save_dir}/{prefix}_{i}.png"

            _log.info("生成配图 %d: %s", i, full_prompt[:50])

            if self._generate_image(full_prompt, save_path, self.INLINE_SIZE):
                saved_paths.append(save_path)

        return saved_paths

    def _generate_image(self, prompt: str, save_path: str, size: str) -> bool:
        """生成并保存图片"""
        try:
            _log.info("调用图片生成 API: model=%s, size=%s", IMAGE_MODEL, size)

            response = self.client.images.generate(
                model=IMAGE_MODEL,
                prompt=prompt,
                size=size,
                n=1,
            )

            _log.debug("API 响应: %s", response)

            image_url = response.data[0].url
            if not image_url:
                _log.warning("未返回图片 URL")
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
            _log.warning("图片生成失败: %s", e)
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
