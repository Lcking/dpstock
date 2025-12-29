"""
Schema Validation Test
测试 Analysis V1 Schema 的完整性和正确性
"""
import json
from datetime import datetime
from schemas.analysis_v1 import (
    AnalysisV1Response,
    StructureType,
    MA200Position,
    Phase,
    PatternType,
    IndicatorSignal,
    RiskLevel,
    StructureStatus,
    JudgmentOptionType,
    JudgmentSnapshot,
    JudgmentOverview
)


def test_analysis_v1_response():
    """测试完整的 Analysis V1 响应"""
    
    # 创建示例数据
    data = {
        "stock_code": "000001",
        "stock_name": "平安银行",
        "market_type": "A",
        "analysis_date": datetime.now(),
        "structure_snapshot": {
            "structure_type": StructureType.CONSOLIDATION,
            "ma200_position": MA200Position.ABOVE,
            "phase": Phase.MIDDLE,
            "key_levels": [
                {"price": 12.50, "label": "近期支撑"},
                {"price": 12.20, "label": "次级支撑"},
                {"price": 13.00, "label": "近期压力"}
            ],
            "trend_description": "价格在MA200上方盘整，区间12.50-13.00，结构完整"
        },
        "pattern_fitting": {
            "pattern_type": PatternType.TRIANGLE,
            "pattern_description": "对称三角形整理，高点逐步降低，低点逐步抬升",
            "completion_rate": 65
        },
        "indicator_translate": {
            "indicators": [
                {
                    "name": "RSI(14)",
                    "value": "52.3",
                    "signal": IndicatorSignal.NEUTRAL,
                    "interpretation": "RSI在中性区域，多空力量均衡"
                },
                {
                    "name": "MACD",
                    "value": "DIF: -0.05, DEA: -0.03",
                    "signal": IndicatorSignal.WEAKENING,
                    "interpretation": "MACD在零轴下方收敛，动能减弱"
                }
            ],
            "global_note": "指标整体显示盘整特征，缺乏方向性信号"
        },
        "risk_of_misreading": {
            "risk_level": RiskLevel.MEDIUM,
            "risk_factors": [
                "三角形末端，方向选择临近",
                "成交量持续萎缩，突破有效性存疑"
            ],
            "risk_flags": ["缩量", "窄幅震荡", "方向不明"],
            "caution_note": "需等待有效突破确认，避免假突破陷阱"
        },
        "judgment_zone": {
            "candidates": [
                {
                    "option_id": "A",
                    "option_type": JudgmentOptionType.STRUCTURE_PREMISE,
                    "description": "若有效突破13.00且放量，结构转为上升"
                },
                {
                    "option_id": "B",
                    "option_type": JudgmentOptionType.STRUCTURE_PREMISE,
                    "description": "若跌破12.50且放量，结构转为下降"
                }
            ],
            "risk_checks": [
                "突破时成交量是否显著放大",
                "突破后能否站稳关键位"
            ],
            "note": "以上为结构分析，非走势预测，系统不提供买卖建议"
        }
    }
    
    # 验证模型
    response = AnalysisV1Response(**data)
    
    # 转换为 JSON
    json_output = response.model_dump_json(indent=2, exclude_none=True)
    
    print("✓ AnalysisV1Response 验证通过")
    print("\n生成的 JSON:")
    print(json_output)
    
    return response


def test_judgment_snapshot():
    """测试判断快照"""
    
    snapshot = JudgmentSnapshot(
        stock_code="000001",
        snapshot_time=datetime.now(),
        structure_premise={
            "structure_type": "consolidation",
            "ma200_position": "above",
            "phase": "middle",
            "pattern_type": "triangle"
        },
        selected_candidates=["A", "C"],
        key_levels_snapshot=[
            {"price": 12.50, "label": "近期支撑"},
            {"price": 13.00, "label": "近期压力"}
        ],
        structure_type=StructureType.CONSOLIDATION,
        ma200_position=MA200Position.ABOVE,
        phase=Phase.MIDDLE
    )
    
    print("\n✓ JudgmentSnapshot 验证通过")
    print(snapshot.model_dump_json(indent=2))
    
    return snapshot


def test_judgment_overview():
    """测试判断概览"""
    
    original = JudgmentSnapshot(
        stock_code="000001",
        snapshot_time=datetime(2025, 12, 20, 10, 0, 0),
        structure_premise={
            "structure_type": "consolidation",
            "ma200_position": "above",
            "phase": "middle"
        },
        selected_candidates=["A"],
        key_levels_snapshot=[
            {"price": 12.50, "label": "近期支撑"},
            {"price": 13.00, "label": "近期压力"}
        ],
        structure_type=StructureType.CONSOLIDATION,
        ma200_position=MA200Position.ABOVE,
        phase=Phase.MIDDLE
    )
    
    overview = JudgmentOverview(
        stock_code="000001",
        original_judgment=original,
        current_structure_status=StructureStatus.BROKEN,
        current_price=13.25,
        price_change_pct=6.0,
        verification_time=datetime.now(),
        status_description="有效突破13.00压力位且放量，结构转为上升",
        reasons=[
            "突破时成交量放大至2倍均量",
            "连续3日站稳13.00上方",
            "MACD金叉向上"
        ]
    )
    
    print("\n✓ JudgmentOverview 验证通过")
    print(overview.model_dump_json(indent=2))
    
    return overview


def test_enum_values():
    """测试所有枚举值"""
    
    print("\n=== 枚举值测试 ===")
    
    print("\nStructureType:")
    for item in StructureType:
        print(f"  - {item.value}")
    
    print("\nMA200Position:")
    for item in MA200Position:
        print(f"  - {item.value}")
    
    print("\nPhase:")
    for item in Phase:
        print(f"  - {item.value}")
    
    print("\nPatternType:")
    for item in PatternType:
        print(f"  - {item.value}")
    
    print("\nIndicatorSignal:")
    for item in IndicatorSignal:
        print(f"  - {item.value}")
    
    print("\nRiskLevel:")
    for item in RiskLevel:
        print(f"  - {item.value}")
    
    print("\nStructureStatus:")
    for item in StructureStatus:
        print(f"  - {item.value}")
    
    print("\nJudgmentOptionType:")
    for item in JudgmentOptionType:
        print(f"  - {item.value}")
    
    print("\n✓ 所有枚举值验证通过")


def generate_openapi_schema():
    """生成 OpenAPI Schema"""
    
    schema = AnalysisV1Response.model_json_schema()
    
    print("\n=== OpenAPI Schema ===")
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    
    # 保存到文件
    with open("schemas/analysis_v1_openapi.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    
    print("\n✓ OpenAPI Schema 已保存到 schemas/analysis_v1_openapi.json")


if __name__ == "__main__":
    print("=" * 60)
    print("Analysis V1 Schema 验证测试")
    print("=" * 60)
    
    try:
        # 测试主响应模型
        test_analysis_v1_response()
        
        # 测试判断快照
        test_judgment_snapshot()
        
        # 测试判断概览
        test_judgment_overview()
        
        # 测试枚举值
        test_enum_values()
        
        # 生成 OpenAPI Schema
        generate_openapi_schema()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
