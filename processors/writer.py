import json
import re
from dataclasses import dataclass, field
from typing import List

from openai import OpenAI

from processors.filter import SelectedItem
from config.settings import (
    DMXAPI_BASE_URL, DMXAPI_API_KEY, LLM_MODEL,
    ARTICLE_MIN_WORDS, ARTICLE_MAX_WORDS,
)
from utils.logger import get_logger

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

    WRITE_SYSTEM = """你是一位优秀的科技媒体作者，文风通俗幽默、深入浅出。

你的任务是：根据大纲撰写一篇公众号文章。

写作要求：
1. 字数控制在 {min_words}-{max_words} 字
2. 语言通俗有趣，像朋友聊天一样
3. 专业内容要解释清楚，不要堆砌术语
4. 每个小节要有承上启下
5. 适当使用表情符号增加可读性
6. 结尾要有总结或展望

输出格式：
- 直接输出 Markdown 格式正文
- 用 ## 表示小节标题
- 用 ![图片描述](image_n.png) 标记配图位置（n 为 1,2,3）"""

    def __init__(self):
        self.client = OpenAI(
            base_url=DMXAPI_BASE_URL,
            api_key=DMXAPI_API_KEY,
        )

    def write(self, items: List[SelectedItem]) -> ArticleResult:
        """两阶段生成文章"""
        _log.info("开始生成文章，素材 %d 条", len(items))

        # 阶段1: 生成大纲
        outline = self._generate_outline(items)
        if not outline:
            _log.error("大纲生成失败")
            raise RuntimeError("大纲生成失败")

        _log.info("大纲生成完成: %s", outline.get("title", ""))

        # 阶段2: 撰写全文
        content_md = self._write_content(items, outline)
        if not content_md:
            _log.error("正文生成失败")
            raise RuntimeError("正文生成失败")

        _log.info("正文生成完成，字数: %d", len(content_md))

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
            return self._parse_outline(content)

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

    def _parse_outline(self, content: str) -> dict:
        """解析大纲 JSON"""
        try:
            json_str = content

            # 尝试多种 JSON 提取方式
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            elif "{" in content:
                # 尝试提取第一个 { 到最后一个 }
                start = content.find("{")
                end = content.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = content[start:end]

            # 清理常见的 JSON 格式问题
            json_str = json_str.strip()
            # 修复中文引号
            json_str = json_str.replace(""", '"').replace(""", '"')
            json_str = json_str.replace("'", '"').replace("'", '"')

            result = json.loads(json_str)

            # 验证必要字段
            if "title" not in result:
                result["title"] = "AI 日报"
            if "sections" not in result:
                result["sections"] = []

            return result

        except json.JSONDecodeError as e:
            _log.error("大纲 JSON 解析失败: %s，内容片段: %s", e, content[:200])
            # 返回一个默认大纲结构
            return {
                "title": "AI 日报",
                "digest": "今日AI热点速览",
                "sections": [],
                "cover_prompt": "AI technology, digital art, futuristic",
            }
        except Exception as e:
            _log.error("大纲解析异常: %s", e)
            return {
                "title": "AI 日报",
                "digest": "今日AI热点速览",
                "sections": [],
                "cover_prompt": "AI technology, digital art, futuristic",
            }

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
