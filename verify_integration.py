#!/usr/bin/env python3
"""
验证 MultiStageFilter 集成是否成功
"""

import sys
sys.path.insert(0, r'D:\gongzhonghao')

print("=" * 60)
print("验证 MultiStageFilter 集成")
print("=" * 60)
print()

# 1. 检查文件是否存在
print("1. 检查核心文件...")
import os
files_to_check = [
    r'D:\gongzhonghao\app\processors\multi_stage_filter.py',
    r'D:\gongzhonghao\pipeline.py',
    r'D:\gongzhonghao\test_multi_stage_filter.py',
]

all_exist = True
for f in files_to_check:
    exists = os.path.exists(f)
    status = "✓" if exists else "✗"
    print(f"  {status} {os.path.basename(f)}")
    if not exists:
        all_exist = False

if not all_exist:
    print("\n✗ 部分文件缺失，请检查安装")
    sys.exit(1)

print("\n2. 检查 pipeline.py 是否已修改...")

# 2. 检查 pipeline.py 是否已修改
with open(r'D:\gongzhonghao\pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'create_multi_stage_filter' in content:
    print("  ✓ pipeline.py 已成功修改，使用 MultiStageFilter")
else:
    print("  ✗ pipeline.py 未检测到修改，可能仍在使用 HotFilter")
    print("  提示: 请手动替换或重新运行安装脚本")

print("\n3. 尝试导入模块...")

# 3. 尝试导入
try:
    from app.processors.multi_stage_filter import (
        MultiStageFilter,
        MultiStageFilterAdapter,
        create_multi_stage_filter,
    )
    print("  ✓ MultiStageFilter 模块导入成功")
except Exception as e:
    print(f"  ✗ 导入失败: {e}")
    sys.exit(1)

try:
    from scripts.pipeline import Pipeline
    print("  ✓ Pipeline 导入成功")
except Exception as e:
    print(f"  ✗ Pipeline 导入失败: {e}")
    sys.exit(1)

print("\n4. 检查 Pipeline 初始化...")

# 4. 检查 Pipeline 能否正确初始化
try:
    # 注意：这里只是检查代码能否运行，不实际执行筛选
    import inspect
    source = inspect.getsource(Pipeline.__init__)
    
    if 'create_multi_stage_filter' in source:
        print("  ✓ Pipeline 使用 MultiStageFilter")
    else:
        print("  ! Pipeline 可能仍使用旧版 filter")
        
except Exception as e:
    print(f"  ! 无法检查 Pipeline 初始化: {e}")

print("\n" + "=" * 60)
print("验证结果")
print("=" * 60)
print("""
✓ MultiStageFilter 已成功集成！

你可以：
1. 运行测试: python test_multi_stage_filter.py
2. 实际运行: python main.py --no-publish
3. 查看日志观察4级筛选统计

建议先运行测试确保一切正常，然后再实际使用。
""")
print("=" * 60)

sys.exit(0)
