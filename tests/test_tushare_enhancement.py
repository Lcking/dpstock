#!/usr/bin/env python3
"""
Tushare Enhancement Test Script
测试增强模块是否正常工作
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置 Token（测试用，实际应从 .env 读取）
# 注意：请将此 Token 添加到 .env 文件中，不要提交到代码库
from dotenv import load_dotenv
load_dotenv()

from services.tushare.orchestrator import enhancement_orchestrator
from services.judgement.builder import judgement_builder
import json


def test_enhancement(ts_code: str = "600519.SH"):
    """测试增强流程"""
    print(f"\n{'='*60}")
    print(f"Testing Enhancement for: {ts_code}")
    print(f"{'='*60}\n")
    
    # 1. 执行增强
    print("[1] Running enhancements...")
    enhancements = enhancement_orchestrator.enhance(ts_code)
    
    print(f"\nAvailable modules: {enhancements.available_modules}")
    print(f"Generated at: {enhancements.generated_at}")
    
    # 2. 显示各模块结果
    modules = {
        'relative_strength': enhancements.relative_strength,
        'industry_position': enhancements.industry_position,
        'capital_flow': enhancements.capital_flow,
        'events': enhancements.events
    }
    
    for name, result in modules.items():
        print(f"\n[{name}]")
        if result:
            print(f"  Available: {result.available}")
            print(f"  Degraded: {result.degraded}")
            print(f"  Summary: {result.summary}")
            if result.key_metrics:
                print(f"  Key Metrics:")
                for m in result.key_metrics:
                    print(f"    - {m.label}: {m.value} {m.unit or ''}")
        else:
            print("  Not available")
    
    # 3. 测试判断区构建
    print(f"\n{'='*60}")
    print("[2] Building Judgment Zone v1.1...")
    
    # 模拟原有候选项
    original_candidates = [
        {"option_id": "A", "description": "若有效突破压力位且放量，结构转为上升"},
        {"option_id": "B", "description": "若跌破支撑位且放量，结构转为下降"},
        {"option_id": "C", "description": "继续在区间内震荡，等待方向明确"}
    ]
    
    module_results = enhancement_orchestrator.get_module_results_dict(ts_code)
    judgment_v11 = judgement_builder.build_judgment_zone_v11(original_candidates, module_results)
    
    print(f"\nJudgment Zone v1.1:")
    print(f"  Version: {judgment_v11.version}")
    print(f"  Candidates: {len(judgment_v11.candidates)}")
    
    for candidate in judgment_v11.candidates:
        print(f"\n  [{candidate.id}] {candidate.text}")
        if candidate.enhanced_premises:
            print(f"    Enhanced Premises:")
            for premise in candidate.enhanced_premises:
                print(f"      - [{premise.domain.value}] {premise.text[:60]}...")
    
    print(f"\n  Risk Checks: {len(judgment_v11.risk_checks)}")
    for check in judgment_v11.risk_checks:
        status = "✓" if check.available else "✗"
        print(f"    [{status}] {check.id}: {check.text[:50]}...")
    
    print(f"\n  Recommended Checks: {judgment_v11.recommended_risk_checks}")
    
    print(f"\n{'='*60}")
    print("Test completed!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # 默认测试茅台
    ts_code = sys.argv[1] if len(sys.argv) > 1 else "600519.SH"
    test_enhancement(ts_code)
