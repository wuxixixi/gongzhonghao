#!/usr/bin/env python3
"""测试 retry 模块导入"""

import sys
sys.path.insert(0, r'D:\gongzhonghao')

try:
    from app.utils.retry import (
        with_retry, 
        with_circuit_breaker, 
        CircuitBreaker,
        CircuitBreakerOpen
    )
    print("✓ retry 模块导入成功")
    
    # 测试装饰器创建
    @with_retry(max_retries=2, base_delay=0.1)
    def test_func():
        return "success"
    
    result = test_func()
    print(f"✓ 装饰器测试成功: {result}")
    
    # 测试断路器
    breaker = CircuitBreaker("test", failure_threshold=3)
    print(f"✓ 断路器创建成功: {breaker.state.value}")
    
    print("\n所有测试通过!")
    
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
