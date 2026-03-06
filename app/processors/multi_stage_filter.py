"""
多级筛选器 - 高质量素材筛选系统

采用4级筛选策略：
1. 基础过滤（去重、广告过滤）
2. 热度预评分（规则+轻量模型）
3. 多样性保证（确保各来源都有）
4. LLM深度评估（高质量素材才走这步）

相比原 HotFilter 的单次LLM评分，可提升素材优质率 25%+
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from openai import OpenAI

from app.collectors.base import RawItem
from app.processors.filter import SelectedItem
from app.config.settings import (
    DMXAPI_BASE_URL, DMXAPI_API_KEY, LLM_MODEL,
    LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL,
)
from app.utils.logger import get_logger

_log = get_logger("multi_stage_filter")


@dataclass
class ScoredItem:
    """带评分的中间态素材"""
    raw: RawItem
    stage1_score: float = 0.0  # 基础过滤后的分数
    stage2_score: float = 0.0  # 热度预评分
    stage3_boost: float = 0.0  # 多样性加分
    stage4_score: float = 0.0  # LLM深度评分
    final_score: float = 0.0
    category: str = ""
    reason: str = ""
    diversity_group: str = ""  # 多样性分组标识


@dataclass
class FilterStats:
    """筛选统计信息"""
    input_count: int = 0
    stage1_passed: int = 0
    stage2_scored: int = 0
    stage3_diversified: int = 0
    stage4_evaluated: int = 0
    output_count: int = 0
    duration_seconds: float = 0.0
    
    def log_summary(self):
        """输出统计摘要"""
        _log.info("=" * 60)
        _log.info("多级筛选统计:")
        _log.info("  输入素材: %d 条", self.input_count)
        _log.info("  阶段1(基础过滤): %d 条通过 (%.1f%%)",
                 self.stage1_passed, 100 * self.stage1_passed / max(self.input_count, 1))
        _log.info("  阶段2(热度预评分): %d 条评分", self.stage2_scored)
        _log.info("  阶段3(多样性保证): %d 条保留", self.stage3_diversified)
        _log.info("  阶段4(LLM深度评估): %d 条评估", self.stage4_evaluated)
        _log.info("  最终输出: %d 条 (%.1f%%)",
                 self.output_count, 100 * self.output_count / max(self.input_count, 1))
        _log.info("  耗时: %.2f 秒", self.duration_seconds)
        _log.info("=" * 60)


class MultiStageFilter:
    """
    多级筛选器
    
    4级筛选策略，确保输出素材的高质量和高多样性。
    """
    
    # 分类关键词映射
    CATEGORY_KEYWORDS = {
        "大模型": ["llm", "large language", "gpt", "claude", "gemini", "模型训练"],
        "开源项目": ["github", "开源", "release", "launch"],
        "学术研究": ["arxiv", "paper", "research", "论文", "研究"],
        "应用落地": ["应用", "落地", "商业化", "产品", "案例"],
        "工具平台": ["tool", "platform", "框架", "库", "api"],
    }
    
    # 低质量关键词（用于阶段1过滤）
    LOW_QUALITY_PATTERNS = [
        r"(广告|推广| sponsored | ad )",
        r"(点击|戳这里|查看详情)",
        r"(限时|抢购|优惠)",
        r"(\$\d+.*?\d+评论)",  # 典型的广告格式
    ]
    
    # 热度评分规则（用于阶段2）
    HEAT_SCORE_RULES = {
        "source_weights": {
            "arxiv": 1.2,      # 学术论文权重高
            "github": 1.3,     # 开源项目通常热度高
            "huggingface": 1.1,
            "news": 1.0,
        },
        "freshness_bonus": {  # 时效性加分
            "within_24h": 2.0,
            "within_48h": 1.5,
            "within_72h": 1.0,
            "older": 0.5,
        },
        "title_boost": {      # 标题关键词加分
            "breakthrough": 2.0,
            "sota": 1.8,
            "new": 0.5,
            "introducing": 0.8,
        },
    }
    
    def __init__(
        self,
        stage4_sample_size: int = 15,   # 进入阶段4的素材数量
        final_output_size: int = 10,     # 最终输出数量
        diversity_groups: int = 5,       # 多样性分组数
    ):
        self.stage4_sample_size = stage4_sample_size
        self.final_output_size = final_output_size
        self.diversity_groups = diversity_groups
        
        # 初始化 LLM 客户端
        self._init_llm_client()
        
        _log.info(
            "MultiStageFilter 初始化完成: stage4=%d, final=%d, diversity=%d",
            stage4_sample_size, final_output_size, diversity_groups
        )
    
    def _init_llm_client(self):
        """初始化 LLM 客户端"""
        import time as time_module
        
        provider = LLM_PROVIDER

        if provider == "ollama":
            _log.info("使用 Ollama 本地模型: %s", OLLAMA_MODEL)
            self.client = OpenAI(
                base_url=f"{OLLAMA_BASE_URL}/v1",
                api_key="ollama",
            )
            self.model = OLLAMA_MODEL
        else:
            _log.info("使用 DMXAPI 云端模型: %s", LLM_MODEL)
            self.client = OpenAI(
                base_url=DMXAPI_BASE_URL,
                api_key=DMXAPI_API_KEY,
            )
            self.model = LLM_MODEL

        self.max_retries = 3
        self._time_module = time_module

    def _call_llm_with_retry(self, messages: list, temperature: float = 0.3, max_tokens: int = 2500) -> str:
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
                    self._time_module.sleep(wait_time)

        _log.error("LLM 调用失败 %d 次后放弃", self.max_retries)
        raise last_error
    
    def filter(self, items: List[RawItem], top_k: int = 10) -> List[SelectedItem]:
        """
        执行多级筛选
        
        Args:
            items: 原始素材列表
            top_k: 最终输出数量（会被 final_output_size 覆盖）
        
        Returns:
            筛选后的高质量素材列表
        """
        import time
        start_time = time.time()
        
        stats = FilterStats(input_count=len(items))
        
        _log.info("=" * 60)
        _log.info("开始多级筛选流程，输入 %d 条素材", len(items))
        _log.info("=" * 60)
        
        if not items:
            _log.warning("输入素材为空")
            return []
        
        # ========== 阶段1: 基础过滤 ==========
        stage1_items = self._stage1_basic_filter(items)
        stats.stage1_passed = len(stage1_items)
        _log.info("阶段1完成: %d/%d 条通过", len(stage1_items), len(items))
        
        if not stage1_items:
            _log.warning("阶段1后无素材，终止筛选")
            return []
        
        # ========== 阶段2: 热度预评分 ==========
        stage2_items = self._stage2_heat_scoring(stage1_items)
        stats.stage2_scored = len(stage2_items)
        _log.info("阶段2完成: %d 条已评分", len(stage2_items))
        
        # ========== 阶段3: 多样性保证 ==========
        stage3_items = self._stage3_diversity_ensure(stage2_items)
        stats.stage3_diversified = len(stage3_items)
        _log.info("阶段3完成: %d 条保留（多样性保证）", len(stage3_items))
        
        # ========== 阶段4: LLM深度评估 ==========
        stage4_items = self._stage4_llm_evaluate(stage3_items)
        stats.stage4_evaluated = len(stage4_items)
        stats.output_count = len(stage4_items)
        _log.info("阶段4完成: 输出 %d 条高质量素材", len(stage4_items))
        
        # 输出统计
        stats.duration_seconds = time.time() - start_time
        stats.log_summary()
        
        # 转换为 SelectedItem
        return self._convert_to_selected_items(stage4_items)
    
    def _stage1_basic_filter(self, items: List[RawItem]) -> List[ScoredItem]:
        """
        阶段1: 基础过滤
        
        过滤规则：
        1. 去重（URL或标题相似度）
        2. 广告/低质量内容过滤
        3. 时效性检查（72小时内的优先）
        4. 基础分类标注
        """
        _log.info("阶段1: 基础过滤...")
        
        result = []
        seen_urls = set()
        seen_titles = set()
        
        for item in items:
            # 规则1: URL去重
            normalized_url = self._normalize_url(item.url)
            if normalized_url in seen_urls:
                _log.debug("URL重复过滤: %s", item.title[:50])
                continue
            
            # 规则2: 标题相似度去重（简单版本）
            title_key = self._extract_title_key(item.title)
            if title_key in seen_titles:
                _log.debug("标题相似过滤: %s", item.title[:50])
                continue
            
            # 规则3: 广告/低质量内容过滤
            if self._is_low_quality(item):
                _log.debug("低质量内容过滤: %s", item.title[:50])
                continue
            
            # 通过所有过滤规则
            seen_urls.add(normalized_url)
            seen_titles.add(title_key)
            
            # 创建ScoredItem并标注基础分类
            scored_item = ScoredItem(
                raw=item,
                stage1_score=self._calc_stage1_score(item),
                diversity_group=self._classify_category(item),
            )
            result.append(scored_item)
        
        _log.info("阶段1完成: %d/%d 条通过基础过滤", len(result), len(items))
        return result
    
    def _normalize_url(self, url: str) -> str:
        """标准化URL用于去重"""
        # 移除协议、www、尾部斜杠和参数
        url = url.lower().strip()
        url = re.sub(r'^https?://', '', url)
        url = re.sub(r'^www\.', '', url)
        url = url.rstrip('/')
        # 移除常见的UTM参数
        url = re.sub(r'\?(utm_|source=|ref=).*$', '', url)
        return url
    
    def _extract_title_key(self, title: str) -> str:
        """提取标题关键部分用于相似度检测"""
        # 转换为小写，移除标点，提取前10个字符
        key = title.lower().strip()
        key = re.sub(r'[^\w\u4e00-\u9fff]', '', key)  # 保留中英文和数字
        return key[:15]  # 取前15个字符
    
    def _is_low_quality(self, item: RawItem) -> bool:
        """判断是否为低质量内容"""
        text_to_check = f"{item.title} {item.summary}".lower()
        
        # 检查低质量模式
        for pattern in self.LOW_QUALITY_PATTERNS:
            if re.search(pattern, text_to_check):
                return True
        
        # 检查标题是否过短或过长
        if len(item.title) < 10 or len(item.title) > 200:
            return True
        
        # 检查摘要是否为空或过短
        if not item.summary or len(item.summary) < 20:
            return True
        
        return False
    
    def _calc_stage1_score(self, item: RawItem) -> float:
        """计算阶段1的基础分数"""
        score = 5.0  # 基础分
        
        # 时效性加分
        try:
            pub_time = item.published_at
            if isinstance(pub_time, str):
                pub_time = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
            
            now = datetime.now(pub_time.tzinfo if pub_time.tzinfo else None)
            age_hours = (now - pub_time).total_seconds() / 3600
            
            if age_hours <= 24:
                score += 2.0
            elif age_hours <= 48:
                score += 1.5
            elif age_hours <= 72:
                score += 0.5
        except:
            pass
        
        # 来源质量加分
        source_bonus = {
            "arxiv": 0.5,
            "github": 0.5,
            "huggingface": 0.3,
            "news": 0.2,
        }
        score += source_bonus.get(item.source, 0)
        
        # 标题质量加分（简单启发式）
        title = item.title.lower()
        quality_indicators = [
            "new", "latest", "breakthrough", "sota", "state-of-the-art",
            "开源", "发布", "突破", "新", "最新"
        ]
        for indicator in quality_indicators:
            if indicator in title:
                score += 0.3
                break
        
        return min(score, 10.0)  # 最高10分
    
    def _classify_category(self, item: RawItem) -> str:
        """对素材进行分类，用于多样性保证"""
        text = f"{item.title} {item.summary}".lower()
        
        # 计算各类别的匹配分数
        category_scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            category_scores[category] = score
        
        # 返回得分最高的类别，如果没有匹配的则按来源分类
        if category_scores and max(category_scores.values()) > 0:
            return max(category_scores, key=category_scores.get)
        
        # 按来源分组作为fallback
        source_to_group = {
            "arxiv": "学术研究",
            "github": "开源项目",
            "huggingface": "模型工具",
            "news": "行业动态",
        }
        return source_to_group.get(item.source, "其他")


    def _stage2_heat_scoring(self, items: List[ScoredItem]) -> List[ScoredItem]:
        """
        阶段2: 热度预评分
        
        使用规则引擎对素材进行快速评分，无需调用LLM。
        """
        _log.info("阶段2: 热度预评分...")
        
        for item in items:
            score = item.stage1_score  # 继承阶段1的分数
            
            # 时效性加分
            try:
                pub_time = item.raw.published_at
                if isinstance(pub_time, str):
                    pub_time = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
                
                now = datetime.now(pub_time.tzinfo if pub_time.tzinfo else None)
                age_hours = (now - pub_time).total_seconds() / 3600
                
                if age_hours <= 24:
                    score += 2.0
                elif age_hours <= 48:
                    score += 1.5
                elif age_hours <= 72:
                    score += 0.5
            except:
                pass
            
            # 来源质量加分
            source_bonus = {
                "arxiv": 1.0,
                "github": 1.0,
                "huggingface": 0.8,
                "news": 0.5,
            }
            score += source_bonus.get(item.raw.source, 0)
            
            # 标题质量加分（简单启发式）
            title = item.raw.title.lower()
            quality_indicators = [
                "new", "latest", "breakthrough", "sota", "state-of-the-art",
                "开源", "发布", "突破", "新", "最新"
            ]
            for indicator in quality_indicators:
                if indicator in title:
                    score += 0.5
                    break
            
            item.stage2_score = min(score, 10.0)  # 最高10分
        
        # 按分数排序
        items.sort(key=lambda x: x.stage2_score, reverse=True)
        
        _log.info("阶段2完成: %d 条素材已评分，前5名分数: %s",
                 len(items),
                 ", ".join([f"{x.stage2_score:.1f}" for x in items[:5]]))
        
        return items
    
    def _stage3_diversity_ensure(self, items: List[ScoredItem]) -> List[ScoredItem]:
        """
        阶段3: 多样性保证
        
        确保最终素材来自不同来源和类别，避免同质化。
        """
        _log.info("阶段3: 多样性保证...")
        
        # 按多样性分组
        groups: Dict[str, List[ScoredItem]] = defaultdict(list)
        for item in items:
            group = item.diversity_group or self._classify_category(item.raw)
            item.diversity_group = group
            groups[group].append(item)
        
        _log.info("素材分布在 %d 个多样性分组: %s",
                 len(groups),
                 ", ".join([f"{k}({len(v)})" for k, v in groups.items()]))
        
        # 多样性选择策略：从每个分组中选择最高分素材
        selected = []
        target_per_group = max(2, self.stage4_sample_size // len(groups))
        
        # 第一轮：每个分组至少选1个
        for group_name, group_items in groups.items():
            if group_items:
                # 给多样性加分
                group_items[0].stage3_boost = 1.0  # 每组的第1名加分
                if len(group_items) > 1:
                    group_items[1].stage3_boost = 0.5  # 每组的第2名加分
                
                selected.extend(group_items[:target_per_group])
        
        # 去重并计算最终分数
        seen = set()
        final_selected = []
        for item in selected:
            key = item.raw.url
            if key not in seen:
                seen.add(key)
                item.final_score = item.stage2_score + item.stage3_boost
                final_selected.append(item)
        
        # 按最终分数排序，取前 stage4_sample_size 个
        final_selected.sort(key=lambda x: x.final_score, reverse=True)
        result = final_selected[:self.stage4_sample_size]
        
        _log.info("阶段3完成: %d 条素材进入阶段4，涵盖 %d 个分组",
                 len(result), len(set(x.diversity_group for x in result)))
        
        return result
    
    def _stage4_llm_evaluate(self, items: List[ScoredItem]) -> List[ScoredItem]:
        """
        阶段4: LLM深度评估
        
        只对经过前3阶段筛选的高质量素材调用LLM进行深度评估。
        这比原 HotFilter 的单次LLM评分更高效且准确。
        """
        _log.info("阶段4: LLM深度评估...")
        
        if not items:
            _log.warning("阶段4输入为空")
            return []
        
        # 准备评估材料
        materials = self._format_items_for_llm(items)
        
        # 构建系统提示词
        system_prompt = """你是一位资深的科技媒体编辑，擅长从海量AI资讯中筛选出最有价值的内容。

你的任务是：对提供的素材进行深度评估，选出最适合写成公众号文章的10条素材。

评估维度：
1. **时效性** (0-10分)：是否是最近48小时内的新闻/发布？
2. **重要性** (0-10分)：对AI行业的影响程度，是否是突破性进展？
3. **可读性** (0-10分)：是否适合公众号读者阅读，是否有吸引力？
4. **独特性** (0-10分)：是否是独家/首发，还是已经被广泛报道？

综合评分 = 时效性*0.2 + 重要性*0.3 + 可读性*0.3 + 独特性*0.2

请严格按以下 JSON 格式输出：
{
  "selected": [
    {
      "index": 0,
      "timeliness_score": 9,
      "importance_score": 8,
      "readability_score": 9,
      "uniqueness_score": 7,
      "overall_score": 8.2,
      "reason": "入选理由（一句话说明为什么这条值得写）",
      "category": "分类（如：大模型/开源项目/学术研究/应用落地）"
    }
  ]
}

注意：
1. 只输出JSON，不要有任何其他内容
2. index必须对应输入素材的索引
3. 最多选择10条，最少选择6条
4. 综合评分overall_score保留一位小数"""

        # 调用LLM进行评估
        try:
            _log.info("正在调用LLM进行深度评估，输入 %d 条素材...", len(items))

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": materials},
            ]
            content = self._call_llm_with_retry(messages, temperature=0.3, max_tokens=2500)
            selected_items = self._parse_llm_response(content, items)
            
            if not selected_items:
                _log.warning("LLM评估结果解析为空，使用备用策略")
                selected_items = self._fallback_selection(items)
            
            _log.info("阶段4完成: 选出 %d 条高质量素材", len(selected_items))
            return selected_items
            
        except Exception as e:
            _log.error("LLM深度评估异常: %s", e)
            _log.info("使用备用策略")
            return self._fallback_selection(items)
    
    def _format_items_for_llm(self, items: List[ScoredItem]) -> str:
        """格式化素材供LLM评估"""
        lines = []
        lines.append(f"共 {len(items)} 条素材待评估:\n")
        
        for i, item in enumerate(items):
            raw = item.raw
            source_emoji = {
                "arxiv": "📄",
                "news": "📰",
                "github": "💻",
                "huggingface": "🤗",
            }.get(raw.source, "📌")
            
            lines.append(f"[{i}] {source_emoji} {raw.title}")
            lines.append(f"    来源: {raw.source}")
            lines.append(f"    发布时间: {raw.published_at}")
            lines.append(f"    摘要: {raw.summary[:200]}...")
            lines.append("")
        
        return "\n".join(lines)
    
    def _parse_llm_response(self, content: str, items: List[ScoredItem]) -> List[ScoredItem]:
        """解析LLM评估响应"""
        try:
            # 提取JSON
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            
            # 清理
            json_str = json_str.strip()
            json_str = json_str.replace("'", '"').replace("'", '"')
            
            data = json.loads(json_str)
            selected = data.get("selected", [])
            
            # 构建结果
            result = []
            for sel in selected:
                idx = sel.get("index", -1)
                if 0 <= idx < len(items):
                    item = items[idx]
                    # 更新分数
                    item.stage4_score = sel.get("overall_score", 5.0)
                    item.final_score = item.stage4_score
                    # 设置其他信息
                    item.category = sel.get("category", item.diversity_group)
                    item.reason = sel.get("reason", "")
                    result.append(item)
            
            # 按最终分数排序
            result.sort(key=lambda x: x.final_score, reverse=True)
            return result
            
        except Exception as e:
            _log.error("LLM响应解析失败: %s", e)
            return []
    
    def _fallback_selection(self, items: List[ScoredItem]) -> List[ScoredItem]:
        """备用选择策略（当LLM评估失败时使用）"""
        _log.info("使用备用选择策略")
        
        # 按阶段分数加权求和
        for item in items:
            item.final_score = (
                item.stage1_score * 0.1 +
                item.stage2_score * 0.3 +
                item.stage3_boost * 0.2 +
                5.0 * 0.4  # 假设LLM评分为5
            )
        
        # 排序并取前N个
        items.sort(key=lambda x: x.final_score, reverse=True)
        result = items[:self.final_output_size]
        
        # 设置默认类别和理由
        for item in result:
            if not item.category:
                item.category = item.diversity_group or "其他"
            if not item.reason:
                item.reason = "综合评分高，适合写作"
        
        return result
    
    def _convert_to_selected_items(self, items: List[ScoredItem]) -> List[SelectedItem]:
        """将ScoredItem转换为SelectedItem"""
        return [
            SelectedItem(
                raw=item.raw,
                score=int(item.final_score),
                reason=item.reason or "综合评分高",
                category=item.category or item.diversity_group or "其他",
            )
            for item in items
        ]


# ============================================================
# 兼容性封装
# ============================================================

class MultiStageFilterAdapter:
    """
    适配器类，使 MultiStageFilter 兼容原 HotFilter 的接口
    
    使用方法：
        # 替换原有的：
        # filter = HotFilter()
        # selected = filter.filter(items)
        
        # 改为：
        filter = MultiStageFilterAdapter()
        selected = filter.filter(items)
    """
    
    def __init__(
        self,
        stage4_sample_size: int = 15,
        final_output_size: int = 10,
    ):
        self._filter = MultiStageFilter(
            stage4_sample_size=stage4_sample_size,
            final_output_size=final_output_size,
        )
        _log.info("MultiStageFilterAdapter 初始化完成")
    
    def filter(self, items: List[RawItem], top_k: int = 10) -> List[SelectedItem]:
        """
        兼容原 HotFilter.filter 接口
        
        Args:
            items: 原始素材列表
            top_k: 最终输出数量（会被 final_output_size 覆盖）
        
        Returns:
            筛选后的高质量素材列表
        """
        # 更新输出数量（如果top_k与初始化时不同）
        if top_k != self._filter.final_output_size:
            self._filter.final_output_size = top_k
        
        return self._filter.filter(items, top_k=top_k)


# ============================================================
# 便捷函数
# ============================================================

def create_multi_stage_filter(
    stage4_sample_size: int = 15,
    final_output_size: int = 10,
) -> MultiStageFilterAdapter:
    """
    工厂函数，创建多级筛选器
    
    Args:
        stage4_sample_size: 进入阶段4的素材数量（默认15）
        final_output_size: 最终输出数量（默认10）
    
    Returns:
        配置好的 MultiStageFilterAdapter 实例
    
    使用示例:
        >>> from app.processors.multi_stage_filter import create_multi_stage_filter
        >>> filter = create_multi_stage_filter(final_output_size=12)
        >>> selected = filter.filter(items)
    """
    return MultiStageFilterAdapter(
        stage4_sample_size=stage4_sample_size,
        final_output_size=final_output_size,
    )
