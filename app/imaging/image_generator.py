"""
图片生成模块
支持多个提供商：DMXAPI (Flux), AiHubMix (Ideogram), Pollinations.ai (免费备用)
"""

from typing import List, Optional
import os

from app.config.settings import (
    DMXAPI_BASE_URL, DMXAPI_API_KEY, IMAGE_MODEL,
    IMAGE_PROVIDER, IDEOGRAM_API_KEY
)
from app.utils.logger import get_logger

_log = get_logger("image_generator")

# 图片最小有效大小（字节）
MIN_IMAGE_SIZE = 1000


class ImageGenerator:
    """
    统一图片生成器 - 支持多个提供商自动切换

    优先级顺序：
    1. 主提供商（根据 IMAGE_PROVIDER 配置）
    2. 备用提供商（主失败时自动切换）
    3. 免费备用服务（Pollinations.ai，无需 API Key）
    """

    def __init__(self):
        self.generators = []
        self._init_generators()

    def _init_generators(self):
        """初始化所有可用的图片生成器"""
        # 根据配置添加主生成器
        if IMAGE_PROVIDER == "v3" and IDEOGRAM_API_KEY:
            from .ideogram_generator import IdeogramGenerator
            self.generators.append(("Ideogram V3", IdeogramGenerator()))
            _log.info("添加主生成器: Ideogram V3 (aihubmix)")

        if IMAGE_PROVIDER == "flux" or not self.generators:
            from .flux_generator import FluxGenerator
            self.generators.append(("Flux", FluxGenerator()))
            _log.info("添加主生成器: Flux (dmxapi)")

        # 添加备用生成器
        if IMAGE_PROVIDER != "v3" and IDEOGRAM_API_KEY:
            from .ideogram_generator import IdeogramGenerator
            self.generators.append(("Ideogram V3 (备用)", IdeogramGenerator()))
            _log.info("添加备用生成器: Ideogram V3 (aihubmix)")

        # 添加免费备用服务（始终添加，作为最后的兜底方案）
        from .free_image_generator import FreeImageGenerator
        self.generators.append(("Pollinations.ai (免费备用)", FreeImageGenerator()))
        _log.info("添加免费备用生成器: Pollinations.ai")

        _log.info("图片生成器初始化完成，共 %d 个可用", len(self.generators))

    def generate_cover(self, prompt: str, save_path: str) -> bool:
        """生成封面图（自动切换备用提供商）"""
        for name, generator in self.generators:
            _log.info("尝试使用 %s 生成封面图...", name)
            try:
                if generator.generate_cover(prompt, save_path):
                    _log.info("使用 %s 成功生成封面图", name)
                    return True
            except Exception as e:
                _log.warning("%s 生成封面图失败: %s", name, e)
                continue

        _log.error("所有图片生成器均失败")
        return False

    def generate_inline_images(
        self,
        prompts: List[str],
        save_dir: str,
        prefix: str = "image"
    ) -> List[str]:
        """生成多张配图（自动切换备用提供商）"""
        saved_paths = []

        for i, prompt in enumerate(prompts[:3], start=1):
            save_path = f"{save_dir}/{prefix}_{i}.png"
            _log.info("生成配图 %d: %s", i, prompt[:50])

            success = False
            for name, generator in self.generators:
                _log.info("尝试使用 %s 生成配图 %d...", name, i)
                try:
                    # 使用单个生成器的配图方法
                    result = generator.generate_cover(prompt, save_path)
                    if result and self._validate_image(save_path):
                        saved_paths.append(save_path)
                        success = True
                        _log.info("使用 %s 成功生成配图 %d", name, i)
                        break
                except Exception as e:
                    _log.warning("%s 生成配图 %d 失败: %s", name, i, e)
                    continue

            if not success:
                _log.error("配图 %d 所有生成器均失败", i)

        return saved_paths

    def _validate_image(self, image_path: str) -> bool:
        """验证图片是否有效"""
        from PIL import Image

        try:
            if not os.path.exists(image_path):
                return False

            file_size = os.path.getsize(image_path)
            if file_size < MIN_IMAGE_SIZE:
                _log.warning("图片文件过小: %d bytes", file_size)
                return False

            with Image.open(image_path) as img:
                img.verify()

            with Image.open(image_path) as img:
                img.load()

            return True
        except Exception as e:
            _log.warning("图片验证失败: %s", e)
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


# 创建默认实例
def get_image_generator():
    """获取图片生成器实例"""
    return ImageGenerator()
