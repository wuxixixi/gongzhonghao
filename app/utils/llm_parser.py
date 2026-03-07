"""
LLM 响应解析工具

提供统一的 JSON 解析功能，处理 LLM 返回的各种格式。
"""

import json
import re
from typing import TypeVar, Type, Optional, Any

from pydantic import BaseModel, ValidationError

from app.utils.logger import get_logger

_log = get_logger("llm_parser")

T = TypeVar("T", bound=BaseModel)


class LLMResponseParser:
    """
    LLM 响应解析器
    
    处理 LLM 返回的各种格式：
    - 纯 JSON
    - 代码块包裹的 JSON (```json ... ```)
    - 混合文本中的 JSON
    
    使用方法：
        from app.utils.llm_parser import LLMResponseParser
        
        # 解析为字典
        data = LLMResponseParser.extract_json(content)
        
        # 解析为 Pydantic 模型
        result = LLMResponseParser.parse_as_model(content, MyModel)
    """
    
    @staticmethod
    def extract_json(content: str) -> str:
        """
        从 LLM 响应中提取 JSON 字符串
        
        Args:
            content: LLM 返回的内容
            
        Returns:
            提取的 JSON 字符串
            
        Raises:
            ValueError: 未找到有效 JSON
        """
        if not content:
            raise ValueError("内容为空")
        
        json_str = content.strip()
        
        # 1. 处理 ```json 代码块
        if "```json" in json_str:
            parts = json_str.split("```json")
            if len(parts) > 1:
                json_str = parts[1].split("```")[0]
        # 2. 处理普通代码块
        elif "```" in json_str:
            blocks = json_str.split("```")
            for block in blocks:
                if "{" in block and "}" in block:
                    json_str = block
                    break
        
        # 3. 提取第一个完整的 JSON 对象
        start = json_str.find("{")
        if start == -1:
            # 尝试提取数组
            start = json_str.find("[")
            if start == -1:
                raise ValueError("未找到 JSON 对象或数组")
        
        # 找到匹配的结束括号
        if json_str[start] == "{":
            end = LLMResponseParser._find_matching_brace(json_str, start)
        else:
            end = LLMResponseParser._find_matching_bracket(json_str, start)
        
        if end == -1:
            raise ValueError("未找到有效的 JSON 结束标记")
        
        json_str = json_str[start:end + 1]
        
        # 4. 清理常见格式问题
        json_str = LLMResponseParser._clean_json(json_str)
        
        return json_str
    
    @staticmethod
    def _find_matching_brace(s: str, start: int) -> int:
        """找到匹配的右大括号"""
        depth = 0
        in_string = False
        escape = False
        
        for i in range(start, len(s)):
            c = s[i]
            
            if escape:
                escape = False
                continue
            
            if c == "\\":
                escape = True
                continue
            
            if c == '"' and not escape:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i
        
        return -1
    
    @staticmethod
    def _find_matching_bracket(s: str, start: int) -> int:
        """找到匹配的右中括号"""
        depth = 0
        in_string = False
        escape = False
        
        for i in range(start, len(s)):
            c = s[i]
            
            if escape:
                escape = False
                continue
            
            if c == "\\":
                escape = True
                continue
            
            if c == '"' and not escape:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    return i
        
        return -1
    
    @staticmethod
    def _clean_json(json_str: str) -> str:
        """清理 JSON 字符串中的常见问题"""
        # 替换中文引号
        json_str = json_str.replace(""", '"').replace(""", '"')
        json_str = json_str.replace("'", '"').replace("'", '"')
        
        # 移除反引号
        json_str = json_str.replace("`", "")
        
        # 移除尾随逗号
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # 移除注释（JSON 标准不支持，但 LLM 可能生成）
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        return json_str.strip()
    
    @staticmethod
    def parse_as_dict(content: str) -> dict:
        """
        解析为字典
        
        Args:
            content: LLM 返回的内容
            
        Returns:
            解析后的字典
        """
        json_str = LLMResponseParser.extract_json(content)
        return json.loads(json_str)
    
    @staticmethod
    def parse_as_model(content: str, model_class: Type[T]) -> T:
        """
        解析为 Pydantic 模型
        
        Args:
            content: LLM 返回的内容
            model_class: Pydantic 模型类
            
        Returns:
            解析后的模型实例
            
        Raises:
            ValueError: 解析失败
            ValidationError: 模型验证失败
        """
        json_str = LLMResponseParser.extract_json(content)
        return model_class.model_validate_json(json_str)
    
    @staticmethod
    def safe_parse_as_dict(content: str, default: Optional[dict] = None) -> dict:
        """
        安全解析为字典（失败时返回默认值）
        
        Args:
            content: LLM 返回的内容
            default: 解析失败时的默认返回值
            
        Returns:
            解析后的字典或默认值
        """
        try:
            return LLMResponseParser.parse_as_dict(content)
        except Exception as e:
            _log.warning("JSON 解析失败: %s", e)
            return default if default is not None else {}
    
    @staticmethod
    def safe_parse_as_model(
        content: str,
        model_class: Type[T],
        default: Optional[T] = None
    ) -> Optional[T]:
        """
        安全解析为模型（失败时返回默认值）
        
        Args:
            content: LLM 返回的内容
            model_class: Pydantic 模型类
            default: 解析失败时的默认返回值
            
        Returns:
            解析后的模型实例或默认值
        """
        try:
            return LLMResponseParser.parse_as_model(content, model_class)
        except (ValueError, ValidationError) as e:
            _log.warning("模型解析失败: %s", e)
            return default
    
    @staticmethod
    def extract_field(content: str, field_name: str) -> Optional[str]:
        """
        从内容中提取特定字段的值
        
        Args:
            content: LLM 返回的内容
            field_name: 字段名
            
        Returns:
            字段值或 None
        """
        patterns = [
            rf'"{field_name}"\s*:\s*"([^"]+)"',
            rf'"{field_name}"\s*:\s*([^,\n}}]+)',
            rf'{field_name}\s*[:=]\s*"([^"]+)"',
            rf'{field_name}\s*[:=]\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                value = match.group(1).strip()
                # 清理引号和尾部标点
                value = value.strip('"').strip("'").strip(",")
                return value
        
        return None


# 预定义的常用模型

class OutlineSection(BaseModel):
    """大纲小节"""
    heading: str
    points: list[str] = []
    source_indices: list[int] = []
    image_hint: str = ""


class ArticleOutline(BaseModel):
    """文章大纲"""
    title: str
    digest: str = ""
    sections: list[OutlineSection] = []
    cover_prompt: str = ""


class QualityCheckItem(BaseModel):
    """质量检查结果"""
    passed: bool
    grammar_issues: list[str] = []
    logic_issues: list[str] = []
    completeness_issues: list[str] = []
    accuracy_issues: list[str] = []
    overall_score: int = 5
    suggestions: list[str] = []
    summary: str = ""


class FilterSelectionItem(BaseModel):
    """筛选结果项"""
    index: int
    timeliness_score: int = 5
    importance_score: int = 5
    readability_score: int = 5
    uniqueness_score: int = 5
    overall_score: float = 5.0
    reason: str = ""
    category: str = ""


class FilterSelectionResult(BaseModel):
    """筛选结果"""
    selected: list[FilterSelectionItem] = []
