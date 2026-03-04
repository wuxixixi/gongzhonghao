import json
import re
from dataclasses import dataclass, field
from typing import List

from openai import OpenAI

from app.processors.filter import SelectedItem
from app.processors.quality_checker import ArticleQualityChecker, ArticleReviser, QualityCheckResult
from app.config.settings import (
    DMXAPI_BASE_URL, DMXAPI_API_KEY, LLM_MODEL,
    ARTICLE_MIN_WORDS, ARTICLE_MAX_WORDS,
)
from app.utils.logger import get_logger

_log = get_logger("writer")


@dataclass
class ArticleResult:
    """文章生成结果"""
    title: str                           # 文章标题
    content_markdown: str                # Markdown 正文
    content_html: str                    # HTML 正文
    digest: str                          # 摘要（用于微信）
    cover_prompt: str                    # 封面图生成提示
    image_prompts: List[str] = field(default_factory=list)  # 3张配图提示


class ArticleWriter:
    """文章撰写器 - 两阶段生成公众号文章"""

    # 质量检查相关配置
    MAX_REVISION_ATTEMPTS = 2  # 最多修订次数
    PASSING_SCORE = 7          # 通过质量检查的最低分数

    OUTLINE_SYSTEM = """你是一位资深科技媒体主编，擅长策划爆款公众号文章。

你的任务是：根据筛选出的AI热点资讯，设计一篇公众号文章的大纲。

要求：
1. 标题要有吸引力，能引发好奇心，但不要标题党
2. 结构清晰，3-5个小节
3. 每个小节要有明确的主题和素材来源
4. 标注配图位置（至少3处）

请严格按以下 JSON 格式输出：
{
  "title": "文章标题",
  "digest": "一句话摘要（50字以内）",
  "sections": [
    {
      "heading": "小节标题",
      "points": ["要点1", "要点2"],
      "source_indices": [0, 1],
      "image_hint": "配图描述"
    }
  ],
  "cover_prompt": "封面图生成提示（英文，描述科技感场景）"
}"""

    WRITE_SYSTEM = """你是一位优秀的科技媒体作者，文风通俗幽默、深入浅出，兼具技术深度和趣味性。

你的任务是：根据大纲撰写一篇公众号文章。

写作要求：
1. 字数严格控制在 {min_words}-{max_words} 字（这是硬性要求）
2. 语言通俗有趣，像和朋友聊天一样亲切
3. 技术内容要解释清楚原理，不要堆砌术语
4. 每个小节要有承上启下的过渡句
5. 适当使用表情符号增加可读性
6. 融入幽默元素让文章生动有趣（但不要过度玩梗）
7. 结尾要有总结或展望
8. 结构清晰，逻辑严谨，适合公众号读者阅读

内容质量要求：
- 包含详细的技术解析、原理说明或行业洞察
- 具备技术深度，信息量充实
- 保持专业性的同时增加趣味性

输出格式：
- 直接输出 Markdown 格式正文
- 用 ## 表示小节标题
- 用 ![图片描述](image_n.png) 标记配图位置（n 为 1,2,3）"""

    def __init__(self):
        self.client = OpenAI(
            base_url=DMXAPI_BASE_URL,
            api_key=DMXAPI_API_KEY,
        )
        # 初始化质量检查器和修订器
        self.quality_checker = ArticleQualityChecker()
        self.reviser = ArticleReviser()

    def write(self, items: List[SelectedItem]) -> ArticleResult:
        """两阶段生成文章（含质量检查）"""
        _log.info("开始生成文章，素材 %d 条", len(items))

        # 阶段1: 生成大纲
        outline = self._generate_outline(items)

        # 如果大纲生成失败，使用默认大纲
        if not outline or not outline.get("sections"):
            _log.warning("大纲生成失败，使用默认结构")
            outline = self._create_default_outline(items)

        _log.info("大纲生成完成: %s", outline.get("title", ""))

        # 阶段2: 撰写全文
        content_md = self._write_content(items, outline)
        if not content_md:
            _log.error("正文生成失败")
            raise RuntimeError("正文生成失败")

        _log.info("正文生成完成，字数: %d", len(content_md))

        # 阶段3: 质量检查与修订
        content_md = self._quality_check_and_revise(content_md, outline)

        # 提取配图提示
        image_prompts = self._extract_image_prompts(outline)

        # Markdown 转 HTML
        content_html = self._markdown_to_html(content_md)

        return ArticleResult(
            title=outline.get("title", "AI 日报"),
            content_markdown=content_md,
            content_html=content_html,
            digest=outline.get("digest", ""),
            cover_prompt=outline.get("cover_prompt", "AI technology, digital art, futuristic"),
            image_prompts=image_prompts,
        )

    def write_for_deep_analysis(
        self,
        selected_item: SelectedItem,
        original_content: str,
    ) -> ArticleResult:
        """针对深度分析场景生成文章

        Args:
            selected_item: 选中的文章
            original_content: 原文内容

        Returns:
            文章生成结果
        """
        _log.info("开始深度分析文章生成")
        _log.info("原文长度: %d 字", len(original_content))

        # 构建深度分析提示
        outline = self._generate_deep_analysis_outline(selected_item, original_content)

        if not outline or not outline.get("sections"):
            _log.warning("深度分析大纲生成失败，使用默认结构")
            outline = self._create_default_outline([selected_item])

        _log.info("深度分析大纲生成完成: %s", outline.get("title", ""))

        # 撰写深度分析正文
        content_md = self._write_deep_analysis_content(
            selected_item, original_content, outline
        )

        if not content_md:
            _log.error("深度分析正文生成失败")
            raise RuntimeError("深度分析正文生成失败")

        _log.info("深度分析正文生成完成，字数: %d", len(content_md))

        # 质量检查与修订
        content_md = self._quality_check_and_revise(content_md, outline)

        # 提取配图提示
        image_prompts = self._extract_image_prompts(outline)

        # Markdown 转 HTML
        content_html = self._markdown_to_html(content_md)

        return ArticleResult(
            title=outline.get("title", "AI 深度分析"),
            content_markdown=content_md,
            content_html=content_html,
            digest=outline.get("digest", ""),
            cover_prompt=outline.get("cover_prompt", "AI technology, digital art, futuristic"),
            image_prompts=image_prompts,
        )

    DEEP_ANALYSIS_OUTLINE_SYSTEM = """你是一位资深的AI技术媒体主编，擅长策划深度技术分析文章。

你的任务是：根据原文内容，设计一篇有深度的公众号文章大纲。

要求：
1. 标题要有技术深度，能引发读者兴趣
2. 结构清晰，3-4个小节
3. 每个小节要有明确的技术解析要点
4. 标注配图位置（至少3处）
5. 大纲要体现技术原理和行业洞察

请严格按以下 JSON 格式输出：
{
  "title": "文章标题",
  "digest": "一句话摘要（50字以内）",
  "sections": [
    {
      "heading": "小节标题",
      "points": ["要点1", "要点2"],
      "image_hint": "配图描述"
    }
  ],
  "cover_prompt": "封面图生成提示（英文，描述科技感场景）"
}"""

    DEEP_ANALYSIS_WRITE_SYSTEM = """你是一位资深的AI技术媒体作者，擅长撰写深入浅出的技术分析文章。

你的任务是：根据原文和大纲，撰写一篇有深度的公众号文章。

写作要求：
1. 字数严格控制在 {min_words}-{max_words} 字（这是硬性要求）
2. 技术内容要详细解释原理，包含技术细节
3. 适当融入幽默元素，让文章生动有趣
4. 每个小节要有承上启下的过渡句
5. 结尾要有总结或展望
6. 结构清晰，逻辑严谨

内容质量要求：
- 详细的技术解析和原理说明
- 行业洞察和独到见解
- 保持专业性的同时增加趣味性

输出格式：
- 直接输出 Markdown 格式正文
- 用 ## 表示小节标题
- 用 ![图片描述](image_n.png) 标记配图位置（n 为 1,2,3）"""

    def _generate_deep_analysis_outline(
        self,
        selected_item: SelectedItem,
        original_content: str,
    ) -> dict:
        """生成深度分析大纲"""
        user_message = f"""请分析以下原文，设计一篇深度分析文章的大纲：

## 原文信息
标题: {selected_item.raw.title}
来源: {selected_item.raw.source}
分类: {selected_item.category}
热度: {selected_item.score}/10
入选理由: {selected_item.reason}

## 原文内容
{original_content[:8000]}

请输出大纲 JSON。"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": self.DEEP_ANALYSIS_OUTLINE_SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            content = response.choices[0].message.content
            return self._parse_outline(content, fallback_title=selected_item.raw.title)

        except Exception as e:
            _log.error("深度分析大纲生成异常: %s", e)
            return {}

    def _write_deep_analysis_content(
        self,
        selected_item: SelectedItem,
        original_content: str,
        outline: dict,
    ) -> str:
        """撰写深度分析正文"""
        outline_text = json.dumps(outline, ensure_ascii=False, indent=2)

        system_prompt = self.DEEP_ANALYSIS_WRITE_SYSTEM.format(
            min_words=ARTICLE_MIN_WORDS,
            max_words=ARTICLE_MAX_WORDS,
        )

        user_message = f"""请根据以下大纲和原文，撰写深度分析文章正文：

## 原文信息
标题: {selected_item.raw.title}
来源: {selected_item.raw.source}
分类: {selected_item.category}
链接: {selected_item.raw.url}

## 原文内容
{original_content[:10000]}

## 文章大纲
{outline_text}

请撰写文章正文。"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.8,
                max_tokens=4500,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            _log.error("深度分析正文生成异常: %s", e)
            return ""

    def _create_default_outline(self, items: List[SelectedItem]) -> dict:
        """创建默认大纲结构"""
        return {
            "title": "今日AI热点速览",
            "digest": "一文速览今日AI领域最新动态",
            "sections": [
                {
                    "heading": "行业动态",
                    "points": ["行业重要新闻"],
                    "source_indices": [0, 1, 2],
                    "image_hint": "AI technology news, digital art"
                },
                {
                    "heading": "技术研究",
                    "points": ["学术研究进展"],
                    "source_indices": [3, 4, 5],
                    "image_hint": "AI research, futuristic lab"
                },
                {
                    "heading": "开源项目",
                    "points": ["热门开源项目"],
                    "source_indices": [6, 7],
                    "image_hint": "Open source code, tech illustration"
                }
            ],
            "cover_prompt": "AI technology, digital art, futuristic, news headline"
        }

    def _generate_outline(self, items: List[SelectedItem]) -> dict:
        """阶段1: 生成大纲"""
        # 格式化素材
        materials = self._format_materials(items)

        user_message = f"""以下是今日热点素材，请设计文章大纲：

{materials}

请输出大纲 JSON。"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": self.OUTLINE_SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            content = response.choices[0].message.content
            # 获取第一个文章的标题作为 fallback
            fallback_title = items[0].raw.title if items else ""
            return self._parse_outline(content, fallback_title=fallback_title)

        except Exception as e:
            _log.error("大纲生成异常: %s", e)
            return {}

    def _write_content(self, items: List[SelectedItem], outline: dict) -> str:
        """阶段2: 撰写全文"""
        # 格式化详细素材
        materials = self._format_detailed_materials(items)

        # 格式化大纲
        outline_text = json.dumps(outline, ensure_ascii=False, indent=2)

        system_prompt = self.WRITE_SYSTEM.format(
            min_words=ARTICLE_MIN_WORDS,
            max_words=ARTICLE_MAX_WORDS,
        )

        user_message = f"""以下是文章大纲和详细素材：

## 大纲
{outline_text}

## 详细素材
{materials}

请根据大纲撰写文章正文。"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.8,
                max_tokens=4000,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            _log.error("正文生成异常: %s", e)
            return ""

    def _quality_check_and_revise(self, content_md: str, outline: dict) -> str:
        """质量检查与修订

        如果质量检查不通过，自动进行修订，最多尝试 MAX_REVISION_ATTEMPTS 次。

        Args:
            content_md: 文章内容
            outline: 大纲信息

        Returns:
            修订后的文章内容
        """
        _log.info("开始质量检查...")

        # 格式化大纲信息
        outline_info = json.dumps(outline, ensure_ascii=False, indent=2)

        for attempt in range(self.MAX_REVISION_ATTEMPTS + 1):
            # 执行质量检查
            check_result = self.quality_checker.check(content_md, outline_info)

            _log.info(
                "质量检查完成: 评分=%d/10, 通过=%s",
                check_result.overall_score,
                check_result.passed
            )

            # 如果通过检查，直接返回
            if check_result.passed:
                _log.info("文章通过质量检查")
                return content_md

            # 如果未通过，检查是否还有修订机会
            if attempt < self.MAX_REVISION_ATTEMPTS:
                _log.warning(
                    "质量检查未通过 (评分: %d/10)，开始第 %d 次修订...",
                    check_result.overall_score,
                    attempt + 1
                )
                # 打印问题摘要
                self._log_check_issues(check_result)

                # 修订文章
                content_md = self.reviser.revise(content_md, check_result)
            else:
                _log.error(
                    "质量检查仍未通过 (评分: %d/10)，达到最大修订次数",
                    check_result.overall_score
                )
                self._log_check_issues(check_result)

        return content_md

    def _log_check_issues(self, result: QualityCheckResult):
        """记录检查问题"""
        if result.grammar_issues:
            _log.warning("语法问题: %s", result.grammar_issues[:3])
        if result.logic_issues:
            _log.warning("逻辑问题: %s", result.logic_issues[:3])
        if result.completeness_issues:
            _log.warning("完整性问题: %s", result.completeness_issues[:3])
        if result.accuracy_issues:
            _log.warning("准确性问题: %s", result.accuracy_issues[:3])
        if result.suggestions:
            _log.info("改进建议: %s", result.suggestions[:3])

    def _format_materials(self, items: List[SelectedItem]) -> str:
        """格式化素材简介"""
        lines = []
        for i, item in enumerate(items):
            lines.append(f"[{i}] 【{item.category}】{item.raw.title}")
            lines.append(f"    热度: {item.score}/10 | 理由: {item.reason}")
            lines.append("")
        return "\n".join(lines)

    def _format_detailed_materials(self, items: List[SelectedItem]) -> str:
        """格式化详细素材"""
        lines = []
        for i, item in enumerate(items):
            lines.append(f"### [{i}] {item.raw.title}")
            lines.append(f"来源: {item.raw.source} | 分类: {item.category}")
            lines.append(f"热度: {item.score}/10")
            lines.append(f"摘要: {item.raw.summary}")
            lines.append(f"链接: {item.raw.url}")
            lines.append("")
        return "\n".join(lines)

    def _parse_outline(self, content: str, fallback_title: str = "") -> dict:
        """解析大纲 JSON

        Args:
            content: LLM 返回的内容
            fallback_title: 解析失败时使用的备用标题
        """
        try:
            json_str = content

            # 尝试多种 JSON 提取方式
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                # 尝试找到代码块中的 JSON
                blocks = content.split("```")
                for block in blocks:
                    if "{" in block and "}" in block:
                        json_str = block
                        break

            # 尝试直接提取 JSON
            if "{" not in json_str:
                # 如果 in json没有找到 JSON，返回默认
                raise ValueError("No JSON found in content")

            # 提取第一个 { 到最后一个 }
            start = json_str.find("{")
            end = json_str.rfind("}") + 1
            if start == -1 or end <= start:
                raise ValueError("Invalid JSON structure")

            json_str = json_str[start:end]

            # 清理常见的 JSON 格式问题
            json_str = json_str.strip()

            # 修复各种引号问题
            json_str = json_str.replace(""", '"').replace(""", '"')
            json_str = json_str.replace("'", '"').replace("'", '"')
            json_str = json_str.replace("`", "")  # 移除反引号

            # 移除可能的尾随逗号
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

            result = json.loads(json_str)

            # 验证必要字段
            if not result.get("title"):
                result["title"] = fallback_title or "深度分析"
            if "sections" not in result:
                result["sections"] = []

            _log.info("大纲解析成功: %s", result.get("title", "")[:30])
            return result

        except (json.JSONDecodeError, ValueError) as e:
            _log.warning("大纲 JSON 解析失败: %s", e)

            # 尝试从原始内容中提取标题
            extracted_title = self._extract_title_from_content(content, fallback_title)

            return {
                "title": extracted_title,
                "digest": "深度分析带你了解最新AI技术",
                "sections": [
                    {"heading": "背景介绍", "content_focus": "介绍文章背景", "image_hint": "AI technology, digital art"},
                    {"heading": "技术原理", "content_focus": "详细技术解析", "image_hint": "AI research, futuristic lab"},
                    {"heading": "应用与展望", "content_focus": "应用场景和未来展望", "image_hint": "Future technology, innovation"},
                ],
                "cover_prompt": f"{fallback_title}, AI technology, deep analysis, digital art" if fallback_title else "AI technology, deep analysis, digital art",
            }
        except Exception as e:
            _log.error("大纲解析异常: %s", e)
            return {
                "title": fallback_title or "深度分析",
                "digest": "深度分析带你了解最新AI技术",
                "sections": [],
                "cover_prompt": "AI technology, deep analysis, digital art",
            }

    def _extract_title_from_content(self, content: str, fallback: str = "") -> str:
        """从 LLM 响应内容中提取标题"""
        try:
            # 尝试匹配 "title": "xxx" 或 title: xxx
            patterns = [
                r'"title"\s*:\s*"([^"]+)"',
                r'"title"\s*:\s*([^,\n]+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    title = match.group(1).strip()
                    # 清理可能的引号
                    title = title.strip('"').strip("'")
                    if title and len(title) > 2:
                        return title

            # 如果没有找到，返回原文标题或默认
            if fallback:
                return fallback

            # 尝试从第一行提取
            lines = content.split("\n")
            for line in lines[:5]:
                line = line.strip()
                if len(line) > 5 and not line.startswith("#"):
                    return line[:50]

            return "深度分析"

        except Exception:
            return fallback or "深度分析"

    def _extract_image_prompts(self, outline: dict) -> List[str]:
        """从大纲中提取配图提示"""
        prompts = []
        sections = outline.get("sections", [])

        for section in sections[:3]:  # 最多3张配图
            hint = section.get("image_hint", "")
            if hint:
                prompts.append(hint)

        # 补齐到3张
        while len(prompts) < 3:
            prompts.append("AI technology illustration, digital art")

        return prompts[:3]

    def _markdown_to_html(self, md: str) -> str:
        """简单的 Markdown 转 HTML"""
        html = md

        # 标题
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)

        # 粗体
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)

        # 斜体
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # 图片
        html = re.sub(r"!\[(.+?)\]\((.+?)\)", r'<img src="\2" alt="\1" style="max-width:100%">', html)

        # 链接
        html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)

        # 段落
        paragraphs = html.split("\n\n")
        html = "".join(
            f"<p>{p.strip()}</p>" if not p.strip().startswith("<") else p
            for p in paragraphs
        )

        return html


# ============================================================
# 深度分析专用写作系统
# ============================================================

DEEP_ANALYSIS_OUTLINE_SYSTEM = """你是一位资深科技媒体主编，擅长策划深度分析类公众号文章。

你的任务是：根据下载的原文内容，设计一篇深度分析文章的大纲。

要求：
1. 标题要有吸引力，能引发好奇心，能体现文章深度
2. 结构清晰，4-6个小节，体现深度分析的特点
3. 每个小节要有明确的主题
4. 标注配图位置（至少3处）
5. 大纲要体现技术深度和独特视角

请严格按以下 JSON 格式输出：
{
  "title": "文章标题",
  "digest": "一句话摘要（50字以内）",
  "sections": [
    {
      "heading": "小节标题",
      "content_focus": "本节重点内容描述",
      "image_hint": "配图描述"
    }
  ],
  "cover_prompt": "封面图生成提示（英文，描述科技感场景）"
}"""

DEEP_ANALYSIS_WRITE_SYSTEM = """你是一位优秀的科技媒体作者，文风通俗幽默、深入浅出，兼具技术深度和趣味性。

你的任务是：根据原文撰写一篇深度分析公众号文章。

写作要求：
1. 字数严格控制在 {min_words}-{max_words} 字（这是硬性要求）
2. 语言通俗有趣，像和朋友聊天一样亲切
3. 技术内容要解释清楚原理，深入剖析
4. 适当融入个人见解和行业洞察
5. 每个小节要有承上启下的过渡句
6. 适当使用表情符号增加可读性
7. 融入幽默元素让文章生动有趣（但不要过度玩梗）
8. 结尾要有深度总结或展望
9. 结构清晰，逻辑严谨，适合公众号读者阅读

内容质量要求：
- 基于原文进行深度分析，不是简单复述
- 包含详细的技术解析、原理说明
- 体现行业洞察和个人见解
- 具备技术深度，信息量充实
- 保持专业性的同时增加趣味性

输出格式：
- 直接输出 Markdown 格式正文
- 用 ## 表示小节标题
- 用 ![图片描述](image_n.png) 标记配图位置（n 为 1,2,3）"""


class DeepAnalysisWriter(ArticleWriter):
    """深度分析文章撰写器"""

    def write_for_deep_analysis(
        self,
        selected_item: SelectedItem,
        original_content: str,
    ) -> ArticleResult:
        """基于原文生成深度分析文章

        Args:
            selected_item: 选中的文章
            original_content: 原文内容

        Returns:
            生成的深度分析文章
        """
        _log.info("开始生成深度分析文章")
        _log.info("原文长度: %d 字", len(original_content))

        # 阶段1: 生成大纲
        outline = self._generate_deep_outline(selected_item, original_content)

        if not outline or not outline.get("sections"):
            _log.warning("大纲生成失败，使用默认结构")
            outline = self._create_default_outline([selected_item])

        _log.info("大纲生成完成: %s", outline.get("title", ""))

        # 阶段2: 撰写全文
        content_md = self._write_deep_content(selected_item, original_content, outline)
        if not content_md:
            _log.error("正文生成失败")
            raise RuntimeError("正文生成失败")

        _log.info("正文生成完成，字数: %d", len(content_md))

        # 质量检查与修订
        content_md = self._quality_check_and_revise(content_md, outline)

        # 提取配图提示
        image_prompts = self._extract_image_prompts(outline)

        # Markdown 转 HTML
        content_html = self._markdown_to_html(content_md)

        return ArticleResult(
            title=outline.get("title", "深度分析"),
            content_markdown=content_md,
            content_html=content_html,
            digest=outline.get("digest", ""),
            cover_prompt=outline.get("cover_prompt", "AI technology, deep analysis, digital art"),
            image_prompts=image_prompts,
        )

    def _generate_deep_outline(self, item: SelectedItem, original_content: str) -> dict:
        """生成深度分析大纲"""
        user_message = f"""请分析以下原文内容，设计一篇深度分析文章的大纲：

## 原文信息
- 标题: {item.raw.title}
- 来源: {item.raw.source}
- 分类: {item.category}
- 链接: {item.raw.url}

## 原文内容
{original_content[:8000]}

请输出大纲 JSON。"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": DEEP_ANALYSIS_OUTLINE_SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            content = response.choices[0].message.content
            return self._parse_outline(content, fallback_title=selected_item.raw.title)

        except Exception as e:
            _log.error("深度分析大纲生成异常: %s", e)
            return {}

    def _write_deep_content(
        self,
        item: SelectedItem,
        original_content: str,
        outline: dict,
    ) -> str:
        """撰写深度分析正文"""
        # 格式化大纲
        outline_text = json.dumps(outline, ensure_ascii=False, indent=2)

        system_prompt = DEEP_ANALYSIS_WRITE_SYSTEM.format(
            min_words=ARTICLE_MIN_WORDS,
            max_words=ARTICLE_MAX_WORDS,
        )

        user_message = f"""请根据以下原文撰写深度分析文章：

## 原文信息
- 标题: {item.raw.title}
- 来源: {item.raw.source}
- 链接: {item.raw.url}

## 文章大纲
{outline_text}

## 原文内容
{original_content}

请根据大纲撰写文章正文。"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.8,
                max_tokens=4500,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            _log.error("深度分析正文生成异常: %s", e)
            return ""
