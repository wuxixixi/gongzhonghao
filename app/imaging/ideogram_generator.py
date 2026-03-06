"""
Ideogram V3 图片生成器
使用 aihubmix API 生成高质量图片
文档: https://docs.aihubmix.com/cn/api/IdeogramAI
"""

import json
import base64
import os
from typing import List, Optional
from pathlib import Path

import requests
from PIL import Image
from io import BytesIO

from app.config.settings import IDEOGRAM_API_KEY, IDEOGRAM_API_URL
from app.utils.logger import get_logger
from app.utils.retry import with_retry, with_circuit_breaker

_log = get_logger("ideogram_generator")

# 图片最小有效大小（字节），用于验证下载的图片
MIN_IMAGE_SIZE = 1000


class IdeogramGenerator:
    """Ideogram V3 图片生成器 - 使用 aihubmix API"""

    # 单张图片最大重试次数
    MAX_SINGLE_IMAGE_RETRIES = 2

    # API 地址
    API_BASE_URL = "https://aihubmix.com/ideogram/v1"
    GENERATE_ENDPOINT = "/ideogram-v3/generate"

    def __init__(self):
        self.api_key = IDEOGRAM_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

    def generate_cover(self, prompt: str, save_path: str) -> bool:
        """生成封面图（带重试）"""
        _log.info("生成封面图: %s", prompt[:50])

        # 封面图重试逻辑
        for attempt in range(self.MAX_SINGLE_IMAGE_RETRIES + 1):
            try:
                if self._generate_image(
                    prompt=prompt,
                    save_path=save_path,
                    aspect_ratio="16x9"  # 宽屏封面
                ):
                    # 验证图片
                    if self._validate_image(save_path):
                        return True
                    else:
                        _log.warning("封面图验证失败，尝试重新生成")
                        if os.path.exists(save_path):
                            os.remove(save_path)
            except Exception as e:
                _log.warning("封面图生成失败 (尝试 %d/%d): %s",
                            attempt + 1, self.MAX_SINGLE_IMAGE_RETRIES + 1, e)

            if attempt < self.MAX_SINGLE_IMAGE_RETRIES:
                _log.info("封面图将进行第 %d 次重试", attempt + 2)

        _log.error("封面图最终生成失败")
        return False

    def generate_inline_images(
        self,
        prompts: List[str],
        save_dir: str,
        prefix: str = "image"
    ) -> List[str]:
        """生成多张配图（单张失败会重试）"""
        saved_paths = []

        for i, prompt in enumerate(prompts[:3], start=1):
            save_path = f"{save_dir}/{prefix}_{i}.png"
            _log.info("生成配图 %d: %s", i, prompt[:50])

            # 单张图片重试逻辑
            success = False
            for attempt in range(self.MAX_SINGLE_IMAGE_RETRIES + 1):
                try:
                    if self._generate_image(
                        prompt=prompt,
                        save_path=save_path,
                        aspect_ratio="1x1"  # 正方形配图
                    ):
                        # 验证图片
                        if self._validate_image(save_path):
                            saved_paths.append(save_path)
                            success = True
                            break
                        else:
                            _log.warning("配图 %d 验证失败，尝试重新生成", i)
                            if os.path.exists(save_path):
                                os.remove(save_path)
                except Exception as e:
                    _log.warning("配图 %d 生成失败 (尝试 %d/%d): %s",
                                i, attempt + 1, self.MAX_SINGLE_IMAGE_RETRIES + 1, e)

                if attempt < self.MAX_SINGLE_IMAGE_RETRIES:
                    _log.info("配图 %d 将进行第 %d 次重试", i, attempt + 2)

            if not success:
                _log.error("配图 %d 最终生成失败，跳过", i)

        return saved_paths

    def _validate_image(self, image_path: str) -> bool:
        """验证图片是否有效"""
        try:
            # 检查文件是否存在
            if not os.path.exists(image_path):
                return False

            # 检查文件大小
            file_size = os.path.getsize(image_path)
            if file_size < MIN_IMAGE_SIZE:
                _log.warning("图片文件过小: %d bytes", file_size)
                return False

            # 尝试打开图片验证格式
            with Image.open(image_path) as img:
                img.verify()

            # 再次打开确认可读取
            with Image.open(image_path) as img:
                img.load()

            return True
        except Exception as e:
            _log.warning("图片验证失败: %s", e)
            return False

    @with_retry(
        max_retries=3,
        base_delay=2.0,
        retry_exceptions=(requests.RequestException,),
    )
    @with_circuit_breaker(
        name="ideogram_image_generation",
        failure_threshold=5,
        recovery_timeout=300.0,
        expected_exception=(Exception,),
    )
    def _generate_image(self, prompt: str, save_path: str, aspect_ratio: str = "1x1") -> bool:
        """调用 Ideogram V3 API 生成图片（带重试和断路器保护）"""
        try:
            url = f"{self.API_BASE_URL}{self.GENERATE_ENDPOINT}"
            _log.info("调用 Ideogram API: url=%s, aspect_ratio=%s", url, aspect_ratio)

            # 使用 multipart/form-data 格式
            data = {
                "prompt": prompt,
                "rendering_speed": "DEFAULT",
                "num_images": "1",
                "aspect_ratio": aspect_ratio,
                "magic_prompt": "AUTO",
                "style_type": "GENERAL",
            }

            response = requests.post(
                url,
                headers=self.headers,
                files={"": ("", "")},  # 触发 multipart/form-data
                data=data,
                timeout=120
            )

            _log.debug("API 响应状态: %s", response.status_code)

            if response.status_code != 200:
                _log.warning("API 请求失败: %s - %s", response.status_code, response.text[:200])
                response.raise_for_status()

            result = response.json()
            _log.debug("API 响应: %s", str(result)[:200])

            # 获取图片 URL
            if "data" not in result or not result["data"]:
                _log.warning("未返回图片数据: %s", result)
                return False

            image_url = result["data"][0].get("url")
            if not image_url:
                _log.warning("未返回图片 URL")
                return False

            # 下载图片
            self._download_image_with_retry(image_url, save_path)

            _log.info("图片已保存: %s", save_path)
            return True

        except Exception as e:
            _log.warning("Ideogram 图片生成失败: %s", e)
            raise

    @with_retry(
        max_retries=3,
        base_delay=1.0,
        retry_exceptions=(requests.RequestException,),
    )
    def _download_image_with_retry(self, image_url: str, save_path: str) -> None:
        """下载图片（带重试）"""
        _log.info("下载图片: %s", image_url[:80])
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()

        # 保存图片
        img = Image.open(BytesIO(img_response.content))
        img.save(save_path, "PNG")

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
