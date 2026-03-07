"""
图片生成模块
支持多个提供商：DMXAPI (Flux), AiHubMix (Ideogram), Pollinations.ai (免费备用)
支持并发生成图片，显著提升生成速度。
"""

from typing import List, Optional
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        output_dir: str,
        parallel: bool = True,
        max_workers: int = 4,
    ) -> dict:
        """
        生成所有图片（封面 + 配图）
        
        Args:
            cover_prompt: 封面图提示词
            image_prompts: 配图提示词列表
            output_dir: 输出目录
            parallel: 是否并发生成（默认 True）
            max_workers: 并发工作线程数
            
        Returns:
            {"cover": 封面路径或 None, "images": 配图路径列表}
        """
        result = {
            "cover": None,
            "images": [],
        }
        
        if parallel:
            return self._generate_all_parallel(cover_prompt, image_prompts, output_dir, max_workers)
        else:
            return self._generate_all_sequential(cover_prompt, image_prompts, output_dir)
    
    def _generate_all_sequential(
        self,
        cover_prompt: str,
        image_prompts: List[str],
        output_dir: str,
    ) -> dict:
        """串行生成所有图片（原逻辑）"""
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
            "图片生成完成(串行): 封面 %s, 配图 %d 张",
            "成功" if result["cover"] else "失败",
            len(result["images"])
        )

        return result
    
    def _generate_all_parallel(
        self,
        cover_prompt: str,
        image_prompts: List[str],
        output_dir: str,
        max_workers: int,
    ) -> dict:
        """
        并发生成所有图片
        
        将封面和配图一起并发提交，显著缩短总耗时。
        预期效果：耗时从 40秒 降至 10-15秒。
        """
        result = {
            "cover": None,
            "images": [None] * min(3, len(image_prompts)),
        }
        
        _log.info("开始并发生成图片: 封面 1 张 + 配图 %d 张", len(image_prompts[:3]))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            # 提交封面生成任务
            cover_path = f"{output_dir}/cover.png"
            futures[executor.submit(
                self._generate_single_with_fallback,
                cover_prompt,
                cover_path,
                "封面"
            )] = ("cover", 0)
            
            # 提交配图生成任务
            for i, prompt in enumerate(image_prompts[:3], start=1):
                save_path = f"{output_dir}/image_{i}.png"
                futures[executor.submit(
                    self._generate_single_with_fallback,
                    prompt,
                    save_path,
                    f"配图{i}"
                )] = ("image", i - 1)
            
            # 收集结果
            for future in as_completed(futures):
                task_type, index = futures[future]
                try:
                    success, path = future.result()
                    if task_type == "cover" and success:
                        result["cover"] = path
                        _log.info("封面图生成成功: %s", path)
                    elif task_type == "image" and success:
                        result["images"][index] = path
                        _log.info("配图 %d 生成成功: %s", index + 1, path)
                except Exception as e:
                    _log.error("%s生成异常: %s", 
                              "封面" if task_type == "cover" else f"配图{index+1}", e)
        
        # 过滤掉失败的配图
        result["images"] = [img for img in result["images"] if img is not None]
        
        _log.info(
            "图片生成完成(并发): 封面 %s, 配图 %d 张",
            "成功" if result["cover"] else "失败",
            len(result["images"])
        )
        
        return result
    
    def _generate_single_with_fallback(
        self,
        prompt: str,
        save_path: str,
        task_name: str,
    ) -> tuple[bool, Optional[str]]:
        """
        使用备用提供商生成单张图片
        
        Args:
            prompt: 提示词
            save_path: 保存路径
            task_name: 任务名称（用于日志）
            
        Returns:
            (是否成功, 图片路径)
        """
        for name, generator in self.generators:
            try:
                if generator.generate_cover(prompt, save_path):
                    if self._validate_image(save_path):
                        return True, save_path
                    else:
                        _log.warning("%s: %s 生成的图片验证失败", task_name, name)
                        if os.path.exists(save_path):
                            os.remove(save_path)
            except Exception as e:
                _log.warning("%s: %s 生成失败: %s", task_name, name, e)
                continue
        
        _log.error("%s: 所有生成器均失败", task_name)
        return False, None


# 创建默认实例
def get_image_generator():
    """获取图片生成器实例"""
    return ImageGenerator()
