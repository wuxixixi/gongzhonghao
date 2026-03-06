import json
import time
from dataclasses import dataclass, field
from typing import List

from openai import OpenAI

from app.collectors.base import RawItem
from app.config.settings import DMXAPI_BASE_URL, DMXAPI_API_KEY, LLM_MODEL
from app.utils.logger import get_logger

_log = get_logger("filter")


@dataclass
class SelectedItem:
    """筛选后的资讯条目"""
    raw: RawItem
    score: int                    # 1-10 热度评分
    reason: str                   # 入选理由
    category: str = ""            # 分类标签


class HotFilter:
    """热点筛选器 - 使用 LLM 从资讯中筛选出最热门的内容"""

    SYSTEM_PROMPT = """你是一位资深科技媒体编辑，擅长从海量AI资讯中筛选出最有价值的内容。

你的任务是：
1. 对每条资讯进行热度评分（1-10分）
2. 筛选出得分最高的 8-12 条
3. 为每条入选资讯给出入选理由

评分标准：
- 10分：突破性进展、重大发布、行业变革
- 8-9分：重要更新、知名公司动态、热门开源项目
- 6-7分：有价值的技术进展、有趣的实验
- 4-5分：普通资讯、增量更新
- 1-3分：噪音、广告、无关内容

请严格按以下 JSON 格式输出，不要输出其他内容：
{
  "selected": [
    {
      "index": 0,
      "score": 9,
      "reason": "入选理由（一句话）",
      "category": "分类（如：大模型/开源项目/学术研究/应用落地）"
    }
  ]
}"""

    def __init__(self):
        self.client = OpenAI(
            base_url=DMXAPI_BASE_URL,
            api_key=DMXAPI_API_KEY,
        )
        self.model = LLM_MODEL
        self.max_retries = 3

    def _call_llm_with_retry(self, messages: list, temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """带重试的 LLM 调用"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                last_error = e
                _log.warning("LLM 调用失败 (尝试 %d/%d): %s", attempt + 1, self.max_retries, e)
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    _log.info("%.1f 秒后重试...", wait_time)
                    time.sleep(wait_time)

        _log.error("LLM 调用失败 %d 次后放弃", self.max_retries)
        raise last_error

    def filter(self, items: List[RawItem], top_k: int = 10) -> List[SelectedItem]:
        """筛选热门资讯"""
        if not items:
            _log.warning("输入资讯列表为空")
            return []

        _log.info("开始筛选热点，输入 %d 条资讯", len(items))

        # 构建用户消息
        items_text = self._format_items(items)
        user_message = f"""以下是今日采集的AI资讯，请筛选出最热门的 {top_k} 条：

{items_text}

请输出筛选结果。"""

        try:
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]
            content = self._call_llm_with_retry(messages, temperature=0.3, max_tokens=2000)
            result = self._parse_response(content, items)

            # 如果解析失败，使用降级策略
            if not result:
                _log.warning("LLM 返回解析失败，使用降级策略")
                result = self._fallback_selection(items, top_k)

            _log.info("筛选完成，选出 %d 条热点", len(result))
            return result

        except Exception as e:
            _log.error("LLM 筛选失败: %s", e)
            # 降级策略：按来源优先级返回
            _log.info("使用降级筛选策略")
            return self._fallback_selection(items, top_k)

    def _format_items(self, items: List[RawItem]) -> str:
        """格式化资讯列表"""
        lines = []
        for i, item in enumerate(items):
            source_emoji = {
                "arxiv": "📄",
                "news": "📰",
                "github": "💻",
                "huggingface": "🤗",
            }.get(item.source, "📌")
            lines.append(f"[{i}] {source_emoji} 【{item.source}】{item.title}")
            lines.append(f"    摘要: {item.summary[:150]}...")
            lines.append("")
        return "\n".join(lines)

    def _parse_response(self, content: str, items: List[RawItem]) -> List[SelectedItem]:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON
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

            data = json.loads(json_str)
            selected = []

            for item_data in data.get("selected", []):
                idx = item_data.get("index", -1)
                if 0 <= idx < len(items):
                    selected.append(SelectedItem(
                        raw=items[idx],
                        score=item_data.get("score", 5),
                        reason=item_data.get("reason", ""),
                        category=item_data.get("category", ""),
                    ))

            # 按分数降序排序
            selected.sort(key=lambda x: x.score, reverse=True)
            return selected

        except json.JSONDecodeError as e:
            _log.error("JSON 解析失败: %s，原始内容: %s", e, content[:200])
            return []
        except Exception as e:
            _log.error("解析响应异常: %s", e)
            return []

    def _fallback_selection(self, items: List[RawItem], top_k: int) -> List[SelectedItem]:
        """降级筛选策略"""
        # 优先级：arxiv > github > huggingface > news
        priority = {"arxiv": 4, "github": 3, "huggingface": 2, "news": 1}

        sorted_items = sorted(
            items,
            key=lambda x: priority.get(x.source, 0),
            reverse=True
        )[:top_k]

        return [
            SelectedItem(
                raw=item,
                score=5,
                reason="按来源优先级筛选",
                category=item.source,
            )
            for item in sorted_items
        ]
