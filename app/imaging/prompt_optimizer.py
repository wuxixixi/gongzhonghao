"""
图片提示词优化器

提供：
- 提示词自动优化
- 多语言翻译
- 风格增强
- 负面提示词处理
"""

import re
from typing import Optional, List
from enum import Enum

from app.utils.logger import get_logger

_log = get_logger("prompt_optimizer")


class ImageStyle(Enum):
    """图片风格"""
    TECH = "tech"           # 科技风格
    MINIMAL = "minimal"     # 极简风格
    CREATIVE = "creative"   # 创意风格
    PROFESSIONAL = "professional"  # 专业风格
    ABSTRACT = "abstract"   # 抽象风格


class PromptOptimizer:
    """
    图片提示词优化器
    
    使用方法：
        from app.imaging.prompt_optimizer import PromptOptimizer
        
        # 优化提示词
        optimized = PromptOptimizer.optimize("AI 技术", style="tech")
    """
    
    # 风格模板
    STYLE_TEMPLATES = {
        ImageStyle.TECH: {
            "prefix": "professional digital art, futuristic technology, ",
            "suffix": ", cyber aesthetic, clean design, high quality, trending on artstation",
            "negative": "blurry, low quality, watermark, text, ugly, deformed",
        },
        ImageStyle.MINIMAL: {
            "prefix": "minimalist design, clean lines, ",
            "suffix": ", simple, elegant, white background, high quality",
            "negative": "complex, cluttered, messy, low quality",
        },
        ImageStyle.CREATIVE: {
            "prefix": "artistic illustration, creative design, ",
            "suffix": ", vibrant colors, unique style, high quality",
            "negative": "boring, plain, low quality, blurry",
        },
        ImageStyle.PROFESSIONAL: {
            "prefix": "professional illustration, ",
            "suffix": ", clean design, business style, high quality",
            "negative": "amateur, low quality, blurry, watermark",
        },
        ImageStyle.ABSTRACT: {
            "prefix": "abstract digital art, ",
            "suffix": ", geometric shapes, modern, high quality",
            "negative": "realistic, photograph, low quality",
        },
    }
    
    # 中文到英文的常见翻译
    TRANSLATIONS = {
        "人工智能": "artificial intelligence",
        "机器学习": "machine learning",
        "深度学习": "deep learning",
        "自然语言处理": "natural language processing",
        "神经网络": "neural network",
        "大模型": "large language model",
        "技术": "technology",
        "科技": "technology",
        "未来": "future",
        "创新": "innovation",
        "数据": "data",
        "算法": "algorithm",
        "智能": "intelligent",
        "自动化": "automation",
        "数字化": "digital",
        "云计算": "cloud computing",
        "大数据": "big data",
        "区块链": "blockchain",
        "量子计算": "quantum computing",
        "机器人": "robot",
        "虚拟现实": "virtual reality",
        "增强现实": "augmented reality",
        "元宇宙": "metaverse",
        "聊天": "chat",
        "对话": "conversation",
        "分析": "analysis",
        "研究": "research",
        "突破": "breakthrough",
        "革命": "revolution",
        "变革": "transformation",
    }
    
    # 增强关键词
    ENHANCEMENT_KEYWORDS = [
        "AI technology",
        "digital art",
        "futuristic",
        "modern",
        "innovative",
        "cutting-edge",
    ]
    
    @classmethod
    def optimize(
        cls,
        prompt: str,
        style: str = "tech",
        enhance: bool = True,
    ) -> str:
        """
        优化图片提示词
        
        Args:
            prompt: 原始提示词
            style: 风格（tech/minimal/creative/professional/abstract）
            enhance: 是否增强提示词
            
        Returns:
            优化后的提示词
        """
        if not prompt:
            return cls._get_default_prompt(style)
        
        # 解析风格
        try:
            image_style = ImageStyle(style.lower())
        except ValueError:
            image_style = ImageStyle.TECH
        
        # 获取风格模板
        template = cls.STYLE_TEMPLATES.get(image_style, cls.STYLE_TEMPLATES[ImageStyle.TECH])
        
        # 翻译中文
        prompt = cls._translate(prompt)
        
        # 清理提示词
        prompt = cls._clean(prompt)
        
        # 应用风格模板
        optimized = f"{template['prefix']}{prompt}{template['suffix']}"
        
        # 增强
        if enhance:
            optimized = cls._add_enhancements(optimized)
        
        _log.debug("提示词优化: '%s' -> '%s'", prompt[:50], optimized[:80])
        
        return optimized
    
    @classmethod
    def optimize_batch(
        cls,
        prompts: List[str],
        style: str = "tech",
    ) -> List[str]:
        """
        批量优化提示词
        
        Args:
            prompts: 提示词列表
            style: 风格
            
        Returns:
            优化后的提示词列表
        """
        return [cls.optimize(p, style) for p in prompts]
    
    @classmethod
    def get_negative_prompt(cls, style: str = "tech") -> str:
        """
        获取负面提示词
        
        Args:
            style: 风格
            
        Returns:
            负面提示词
        """
        try:
            image_style = ImageStyle(style.lower())
        except ValueError:
            image_style = ImageStyle.TECH
        
        template = cls.STYLE_TEMPLATES.get(image_style, cls.STYLE_TEMPLATES[ImageStyle.TECH])
        return template.get("negative", "")
    
    @classmethod
    def _translate(cls, prompt: str) -> str:
        """翻译中文为英文"""
        result = prompt
        for chinese, english in cls.TRANSLATIONS.items():
            result = result.replace(chinese, english)
        return result
    
    @classmethod
    def _clean(cls, prompt: str) -> str:
        """清理提示词"""
        # 移除多余空格
        prompt = re.sub(r'\s+', ' ', prompt)
        # 移除特殊字符
        prompt = re.sub(r'[^\w\s,.-]', '', prompt)
        # 移除首尾空格
        prompt = prompt.strip()
        return prompt
    
    @classmethod
    def _add_enhancements(cls, prompt: str) -> str:
        """添加增强关键词"""
        # 检查是否已包含增强关键词
        for keyword in cls.ENHANCEMENT_KEYWORDS:
            if keyword.lower() in prompt.lower():
                return prompt
        
        # 添加部分增强关键词
        if "AI" not in prompt and "artificial intelligence" not in prompt.lower():
            prompt = f"AI technology, {prompt}"
        
        return prompt
    
    @classmethod
    def _get_default_prompt(cls, style: str) -> str:
        """获取默认提示词"""
        defaults = {
            "tech": "AI technology, futuristic digital art, neural network visualization",
            "minimal": "minimalist technology design, clean lines, simple shapes",
            "creative": "creative AI illustration, vibrant colors, artistic style",
            "professional": "professional technology illustration, business style",
            "abstract": "abstract AI art, geometric shapes, modern design",
        }
        return defaults.get(style, defaults["tech"])
    
    @classmethod
    def generate_cover_prompt(cls, title: str, category: str = "") -> str:
        """
        根据文章标题生成封面图提示词
        
        Args:
            title: 文章标题
            category: 文章分类
            
        Returns:
            封面图提示词
        """
        # 提取关键词
        keywords = cls._extract_keywords(title)
        
        # 组合提示词
        if keywords:
            prompt = ", ".join(keywords[:3])
        else:
            prompt = "AI technology news"
        
        # 添加分类相关内容
        if category:
            category_prompts = {
                "大模型": "large language model, neural network",
                "开源项目": "open source code, github, programming",
                "学术研究": "scientific research, academic paper, innovation",
                "应用落地": "practical application, real-world usage",
                "工具平台": "software tool, platform interface",
            }
            extra = category_prompts.get(category, "")
            if extra:
                prompt = f"{prompt}, {extra}"
        
        return cls.optimize(prompt, style="tech")
    
    @classmethod
    def _extract_keywords(cls, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 移除常见停用词
        stopwords = {"的", "是", "在", "有", "和", "了", "与", "为", "对", "这"}
        
        # 分词（简单实现）
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
        
        # 过滤
        keywords = []
        for word in words:
            if len(word) >= 2 and word not in stopwords:
                keywords.append(word)
        
        return keywords


# 便捷函数
def optimize_prompt(prompt: str, style: str = "tech") -> str:
    """优化图片提示词"""
    return PromptOptimizer.optimize(prompt, style)


def optimize_prompts(prompts: List[str], style: str = "tech") -> List[str]:
    """批量优化图片提示词"""
    return PromptOptimizer.optimize_batch(prompts, style)
