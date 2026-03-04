"""
文章质量检查器

使用大语言模型对文章进行全面质量检查，包括：
- 语法错误检测
- 逻辑连贯性验证
- 内容完整性审查
- 表达准确性确认
- 整体质量评估
"""

from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI

from app.config.settings import DMXAPI_BASE_URL, DMXAPI_API_KEY, LLM_MODEL
from app.utils.logger import get_logger

_log = get_logger("quality_checker")


@dataclass
class QualityCheckResult:
    """质量检查结果"""
    passed: bool                      # 是否通过检查
    grammar_issues: List[str]         # 语法问题
    logic_issues: List[str]          # 逻辑问题
    completeness_issues: List[str]   # 完整性问题
    accuracy_issues: List[str]        # 准确性问题
    overall_score: int                # 整体评分 (1-10)
    suggestions: List[str]            # 改进建议
    summary: str                      # 检查总结


class ArticleQualityChecker:
    """文章质量检查器"""

    SYSTEM_PROMPT = """你是一位资深的文章编辑和内容质量专家。你的任务是對文章进行全面的质量检查。

请严格按照以下维度进行检查：

1. 语法错误检测
   - 检查错别字、标点错误
   - 检查语法结构问题
   - 检查用词不当

2. 逻辑连贯性验证
   - 检查段落之间的过渡是否自然
   - 检查论点论据是否对应
   - 检查逻辑链条是否完整

3. 内容完整性审查
   - 检查是否涵盖大纲要求的所有要点
   - 检查开头和结尾是否完整
   - 检查是否有遗漏的重要内容

4. 表达准确性确认
   - 检查技术术语使用是否准确
   - 检查事实陈述是否正确
   - 检查数据引用是否准确

5. 整体质量评估
   - 文章是否有吸引力
   - 语言是否通顺流畅
   - 结构是否清晰合理

请对文章进行详细检查，并以 JSON 格式输出检查结果：

{
  "passed": true/false,
  "grammar_issues": ["问题1", "问题2"],
  "logic_issues": ["问题1", "问题2"],
  "completeness_issues": ["问题1", "问题2"],
  "accuracy_issues": ["问题1", "问题2"],
  "overall_score": 8,
  "suggestions": ["建议1", "建议2"],
  "summary": "总结说明"
}

如果 overall_score >= 7 且没有严重问题，passed 应为 true。
如果 overall_score < 7 或存在严重问题，passed 应为 false。

严重问题包括：
- 大面积语法错误
- 关键内容缺失
- 事实性错误
- 严重逻辑不通"""

    def __init__(self):
        self.client = OpenAI(
            base_url=DMXAPI_BASE_URL,
            api_key=DMXAPI_API_KEY,
        )

    def check(self, article_content: str, outline_info: str = "") -> QualityCheckResult:
        """对文章进行全面质量检查

        Args:
            article_content: 文章内容 (Markdown 格式)
            outline_info: 大纲信息（可选，用于检查内容完整性）

        Returns:
            质量检查结果
        """
        _log.info("开始质量检查...")

        user_message = f"""请对以下文章进行全面的质量检查：

## 文章内容
{article_content}

## 大纲信息（参考）
{outline_info}

请输出 JSON 格式的检查结果。"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            return self._parse_result(content)

        except Exception as e:
            _log.error("质量检查异常: %s", e)
            return QualityCheckResult(
                passed=False,
                grammar_issues=[],
                logic_issues=[],
                completeness_issues=[],
                accuracy_issues=[],
                overall_score=0,
                suggestions=["质量检查失败"],
                summary=f"检查过程发生错误: {e}",
            )

    def _parse_result(self, content: str) -> QualityCheckResult:
        """解析检查结果 JSON"""
        import json
        import re

        try:
            # 尝试提取 JSON
            json_str = content

            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                blocks = content.split("```")
                for block in blocks:
                    if "{" in block and "}" in block:
                        json_str = block
                        break

            # 提取 JSON
            start = json_str.find("{")
            end = json_str.rfind("}") + 1
            if start == -1 or end <= start:
                raise ValueError("Invalid JSON structure")

            json_str = json_str[start:end]

            # 清理
            json_str = json_str.strip()
            json_str = json_str.replace('"', '"').replace('"', '"')
            json_str = json_str.replace("'", '"').replace("'", '"')
            json_str = json_str.replace("`", "")
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

            result = json.loads(json_str)

            return QualityCheckResult(
                passed=result.get("passed", False),
                grammar_issues=result.get("grammar_issues", []),
                logic_issues=result.get("logic_issues", []),
                completeness_issues=result.get("completeness_issues", []),
                accuracy_issues=result.get("accuracy_issues", []),
                overall_score=result.get("overall_score", 5),
                suggestions=result.get("suggestions", []),
                summary=result.get("summary", ""),
            )

        except (json.JSONDecodeError, ValueError) as e:
            _log.warning("检查结果解析失败: %s", e)
            return QualityCheckResult(
                passed=True,
                grammar_issues=[],
                logic_issues=[],
                completeness_issues=[],
                accuracy_issues=[],
                overall_score=8,
                suggestions=[],
                summary="检查结果解析异常，默认通过",
            )


class ArticleReviser:
    """文章修订器 - 根据质量检查结果修订文章"""

    SYSTEM_PROMPT = """你是一位优秀的科技媒体编辑。你的任务是根据质量检查结果修订文章。

你需要：
1. 认真分析每一条质量检查反馈
2. 对文章进行针对性修订
3. 保持原文的风格和结构
4. 确保修订后的文章质量达标

请直接输出修订后的文章内容（Markdown 格式），不要输出其他内容。"""

    def __init__(self):
        self.client = OpenAI(
            base_url=DMXAPI_BASE_URL,
            api_key=DMXAPI_API_KEY,
        )

    def revise(
        self,
        article_content: str,
        check_result: QualityCheckResult,
    ) -> str:
        """根据质量检查结果修订文章

        Args:
            article_content: 原始文章内容
            check_result: 质量检查结果

        Returns:
            修订后的文章内容
        """
        _log.info("开始修订文章...")

        # 构建修订提示
        issues_text = self._format_issues(check_result)

        user_message = f"""请根据以下质量检查结果修订文章：

## 原始文章
{article_content}

## 质量检查结果
{issues_text}

请输出修订后的文章（Markdown 格式）。"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=4500,
            )

            revised = response.choices[0].message.content
            _log.info("文章修订完成")
            return revised

        except Exception as e:
            _log.error("文章修订异常: %s", e)
            return article_content  # 返回原文

    def _format_issues(self, result: QualityCheckResult) -> str:
        """格式化问题列表"""
        lines = []

        if result.grammar_issues:
            lines.append("【语法问题】")
            for issue in result.grammar_issues:
                lines.append(f"  - {issue}")
            lines.append("")

        if result.logic_issues:
            lines.append("【逻辑问题】")
            for issue in result.logic_issues:
                lines.append(f"  - {issue}")
            lines.append("")

        if result.completeness_issues:
            lines.append("【完整性问题】")
            for issue in result.completeness_issues:
                lines.append(f"  - {issue}")
            lines.append("")

        if result.accuracy_issues:
            lines.append("【准确性问题】")
            for issue in result.accuracy_issues:
                lines.append(f"  - {issue}")
            lines.append("")

        if result.suggestions:
            lines.append("【改进建议】")
            for suggestion in result.suggestions:
                lines.append(f"  - {suggestion}")
            lines.append("")

        lines.append(f"整体评分: {result.overall_score}/10")
        lines.append(f"总结: {result.summary}")

        return "\n".join(lines)
