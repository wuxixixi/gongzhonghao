#!/usr/bin/env python3
"""
MultiStageFilter 集成测试脚本

用于验证多级筛选器的功能是否正常。
"""

import sys
import random
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, r'D:\gongzhonghao')

try:
    from app.collectors.base import RawItem
    from app.processors.multi_stage_filter import (
        MultiStageFilter,
        MultiStageFilterAdapter,
        create_multi_stage_filter,
        ScoredItem,
    )
    print("✓ 所有模块导入成功\n")
except Exception as e:
    print(f"✗ 模块导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def create_test_items(count: int = 50) -> list:
    """创建测试数据"""
    sources = ["arxiv", "github", "huggingface", "news"]
    titles = [
        "GPT-5 即将发布：AI 能力的又一次飞跃",
        "开源大模型 Llama 3.2 发布，性能大幅提升",
        "Google 发布新论文：Transformer 架构的下一步",
        "ChatGPT 用户数突破 3 亿，商业化进展顺利",
        "OpenAI 推出新的图像生成模型 DALL-E 3",
        "NVIDIA 发布新一代 AI 芯片，性能提升 4 倍",
        "Meta 开源新的语音合成模型，效果逼真",
        "阿里巴巴发布通义千问 2.5，中文能力领先",
        "Stability AI 发布 Stable Diffusion 3，画质大幅提升",
        "字节跳动发布新的视频生成模型，效果惊艳",
    ]
    
    items = []
    now = datetime.now()
    
    for i in range(count):
        source = random.choice(sources)
        title = random.choice(titles) if i < len(titles) else f"AI News Item {i}"
        
        # 随机发布时间（0-72小时内）
        hours_ago = random.uniform(0, 72)
        pub_time = now - timedelta(hours=hours_ago)
        
        # 添加一些重复项来测试去重功能
        if i % 10 == 0 and i > 0:
            title = items[i-1].title  # 复制前一个标题
        
        item = RawItem(
            source=source,
            title=title,
            summary=f"这是一个关于 {title} 的摘要。" * 3,
            url=f"https://example.com/{source}/article{i}",
            published_at=pub_time,
            tags=[source, "ai"],
        )
        items.append(item)
    
    return items


def test_basic_functionality():
    """测试基本功能"""
    print("=" * 60)
    print("测试 1: 基本功能测试")
    print("=" * 60)
    
    # 创建测试数据
    items = create_test_items(30)
    print(f"✓ 创建了 {len(items)} 条测试数据\n")
    
    # 创建筛选器
    filter = MultiStageFilterAdapter(
        stage4_sample_size=15,
        final_output_size=10,
    )
    print("✓ 筛选器创建成功\n")
    
    # 执行筛选
    selected = filter.filter(items, top_k=10)
    print(f"✓ 筛选完成，选出 {len(selected)} 条素材\n")
    
    # 验证结果
    assert len(selected) > 0, "筛选结果不应为空"
    assert len(selected) <= 10, f"筛选结果应不超过10条，实际{len(selected)}条"
    
    print("✓ 基本功能测试通过！\n")
    return True


def test_diversity():
    """测试多样性保证"""
    print("=" * 60)
    print("测试 2: 多样性保证测试")
    print("=" * 60)
    
    # 创建均衡分布的测试数据
    items = create_test_items(50)
    print(f"✓ 创建了 {len(items)} 条测试数据\n")
    
    # 统计原始分布
    source_dist = {}
    for item in items:
        source_dist[item.source] = source_dist.get(item.source, 0) + 1
    print("原始来源分布:", source_dist)
    
    # 执行筛选
    filter = create_multi_stage_filter(final_output_size=10)
    selected = filter.filter(items)
    print(f"\n✓ 筛选完成，选出 {len(selected)} 条素材\n")
    
    # 统计结果分布
    result_dist = {}
    for item in selected:
        result_dist[item.raw.source] = result_dist.get(item.raw.source, 0) + 1
    print("筛选后来源分布:", result_dist)
    
    # 验证多样性：至少要有2个不同来源
    unique_sources = len(result_dist)
    assert unique_sources >= 2, f"筛选结果应来自至少2个来源，实际{unique_sources}个"
    
    print(f"\n✓ 多样性保证测试通过！结果来自 {unique_sources} 个不同来源\n")
    return True


def test_edge_cases():
    """测试边界情况"""
    print("=" * 60)
    print("测试 3: 边界情况测试")
    print("=" * 60)
    
    # 测试空输入
    print("\n测试 3.1: 空输入...")
    filter = create_multi_stage_filter()
    result = filter.filter([])
    assert len(result) == 0, "空输入应返回空结果"
    print("✓ 空输入处理正确\n")
    
    # 测试少量输入
    print("测试 3.2: 少量输入（5条）...")
    items = create_test_items(5)
    result = filter.filter(items)
    assert len(result) <= 5, "结果数量不应超过输入数量"
    print(f"✓ 少量输入处理正确，输出 {len(result)} 条\n")
    
    # 测试大量输入
    print("测试 3.3: 大量输入（100条）...")
    items = create_test_items(100)
    result = filter.filter(items)
    assert len(result) <= 10, "大量输入时结果应被限制在10条以内"
    print(f"✓ 大量输入处理正确，从100条中选出 {len(result)} 条\n")
    
    print("✓ 边界情况测试全部通过！\n")
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("MultiStageFilter 集成测试")
    print("=" * 60 + "\n")
    
    try:
        # 运行所有测试
        test_basic_functionality()
        test_diversity()
        test_edge_cases()
        
        # 测试完成
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60 + "\n")
        
        # 提供使用建议
        print("使用建议：")
        print("-" * 60)
        print("""
1. 在 pipeline.py 中替换原有的 HotFilter：

   # 原来的代码：
   # from app.processors.filter import HotFilter
   # self.filter = HotFilter()
   
   # 替换为：
   from app.processors.multi_stage_filter import create_multi_stage_filter
   self.filter = create_multi_stage_filter(
       stage4_sample_size=15,
       final_output_size=10,
   )

2. 运行测试确保集成成功：
   
   python test_multi_stage_filter.py

3. 查看详细日志：
   - 日志会输出每阶段的详细统计
   - 可以通过日志分析筛选效果

4. 调整参数：
   - stage4_sample_size: 控制进入LLM评估的素材数量
   - final_output_size: 控制最终输出数量
   - 可以根据实际需求调整
""")
        print("-" * 60 + "\n")
        
        return 0
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ 测试失败！")
        print("=" * 60)
        print(f"\n错误: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())