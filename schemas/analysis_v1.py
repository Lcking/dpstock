"""
Analysis V1 Response Schema
固定五段式结构分析响应模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


# ============ Enums ============

class StructureType(str, Enum):
    """结构类型"""
    UPTREND = "uptrend"  # 上升趋势
    DOWNTREND = "downtrend"  # 下降趋势
    CONSOLIDATION = "consolidation"  # 盘整


class MA200Position(str, Enum):
    """MA200位置关系"""
    ABOVE = "above"  # 价格在MA200上方
    BELOW = "below"  # 价格在MA200下方
    NEAR = "near"  # 价格接近MA200
    NO_DATA = "no_data"  # 无MA200数据


class Phase(str, Enum):
    """阶段"""
    EARLY = "early"  # 早期
    MIDDLE = "middle"  # 中期
    LATE = "late"  # 后期
    UNCLEAR = "unclear"  # 不明确


class PatternType(str, Enum):
    """形态类型"""
    HEAD_SHOULDERS = "head_shoulders"  # 头肩顶/底
    DOUBLE_TOP_BOTTOM = "double_top_bottom"  # 双顶/底
    TRIANGLE = "triangle"  # 三角形
    CHANNEL = "channel"  # 通道
    WEDGE = "wedge"  # 楔形
    FLAG = "flag"  # 旗形
    NONE = "none"  # 无明显形态


class IndicatorSignal(str, Enum):
    """指标信号"""
    STRENGTHENING = "strengthening"  # 强化中
    WEAKENING = "weakening"  # 弱化中
    EXTREME = "extreme"  # 极值区
    NEUTRAL = "neutral"  # 中性


class RiskLevel(str, Enum):
    """风险等级"""
    HIGH = "high"  # 高风险
    MEDIUM = "medium"  # 中风险
    LOW = "low"  # 低风险


class StructureStatus(str, Enum):
    """结构状态"""
    MAINTAINED = "maintained"  # 结构保持
    WEAKENED = "weakened"  # 结构被削弱
    BROKEN = "broken"  # 结构被破坏


# ============ Section Models ============

class PriceLevel(BaseModel):
    """价格位"""
    price: float = Field(..., description="价格")
    label: str = Field(..., description="标签，如'支撑位1'、'压力位2'")


class StructureSnapshot(BaseModel):
    """Section 1: Structure Snapshot - 结构快照"""
    structure_type: StructureType = Field(..., description="当前结构类型")
    ma200_position: MA200Position = Field(..., description="价格与MA200的位置关系")
    phase: Phase = Field(..., description="当前所处阶段")
    key_levels: List[PriceLevel] = Field(..., description="关键价格位（支撑/压力）", max_length=6)
    trend_description: str = Field(..., description="趋势描述（简短）", max_length=200)


class PatternFitting(BaseModel):
    """Section 2: Pattern Fitting - 形态拟合"""
    pattern_type: PatternType = Field(..., description="识别的形态类型")
    pattern_description: str = Field(..., description="形态描述", max_length=200)
    completion_rate: Optional[int] = Field(None, ge=0, le=100, description="形态完成度（百分比）")


class IndicatorItem(BaseModel):
    """单个指标翻译"""
    name: str = Field(..., description="指标名称，如'RSI'、'MACD'")
    value: str = Field(..., description="指标值（格式化字符串）")
    signal: IndicatorSignal = Field(..., description="信号方向")
    interpretation: str = Field(..., description="指标解读", max_length=150)


class IndicatorTranslate(BaseModel):
    """Section 3: Indicator Translate - 指标翻译"""
    indicators: List[IndicatorItem] = Field(..., description="指标列表", max_length=5)
    global_note: str = Field(..., description="指标整体说明", max_length=200)


class MisreadingRisk(BaseModel):
    """Section 4: Risk of Misreading - 误读风险"""
    risk_level: RiskLevel = Field(..., description="误读风险等级")
    risk_factors: List[str] = Field(..., description="风险因素列表", max_length=4)
    risk_flags: List[str] = Field(..., description="风险标记（如'背离'、'缩量'）", max_length=5)
    caution_note: str = Field(..., description="注意事项", max_length=200)


class JudgmentOptionType(str, Enum):
    """判断选项类型"""
    STRUCTURE_PREMISE = "structure_premise"  # 结构前提
    EXECUTION_METHOD = "execution_method"  # 执行方式
    RISK_CHECK = "risk_check"  # 风险确认


class JudgmentOption(BaseModel):
    """判断候选项"""
    option_id: str = Field(..., description="选项ID，如'A'、'B'、'C'")
    option_type: JudgmentOptionType = Field(..., description="选项类型")
    description: str = Field(..., description="判断描述（结构前提/执行方式/风险确认）", max_length=150)


class JudgmentZone(BaseModel):
    """Section 5: Judgment Zone - 判断候选区"""
    candidates: List[JudgmentOption] = Field(..., description="判断候选项（结构前提）", min_length=2, max_length=4)
    risk_checks: List[str] = Field(..., description="风险确认项", max_length=3)
    note: str = Field(..., description="说明：系统不提供买卖建议", max_length=100)


# ============ Judgment Models ============

class JudgmentSnapshot(BaseModel):
    """用户判断快照（用于保存完整结构前提集合）"""
    stock_code: str = Field(..., description="股票代码")
    snapshot_time: datetime = Field(..., description="快照时间")
    structure_premise: Dict[str, Any] = Field(..., description="完整结构前提集合")
    selected_candidates: List[str] = Field(..., description="用户选择的候选项ID列表")
    key_levels_snapshot: List[PriceLevel] = Field(..., description="关键价格位快照")
    structure_type: StructureType = Field(..., description="结构类型")
    ma200_position: MA200Position = Field(..., description="MA200位置")
    phase: Phase = Field(..., description="阶段")
    verification_period: int = Field(default=7, description="验证周期（天）")


class JudgmentOverview(BaseModel):
    """判断概览（用于展示结构验证结果）"""
    stock_code: str = Field(..., description="股票代码")
    original_judgment: JudgmentSnapshot = Field(..., description="原始判断")
    current_structure_status: StructureStatus = Field(..., description="当前结构状态")
    current_price: float = Field(..., description="当前价格")
    price_change_pct: float = Field(..., description="价格变化百分比")
    verification_time: datetime = Field(..., description="验证时间")
    status_description: str = Field(..., description="状态描述", max_length=200)
    reasons: List[str] = Field(..., description="状态判定原因", max_length=5)


# ============ Main Response Model ============

class AnalysisV1Response(BaseModel):
    """Analysis V1 完整响应（固定五段式）"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    market_type: str = Field(..., description="市场类型", examples=["A", "HK", "US"])
    analysis_date: datetime = Field(..., description="分析日期")
    
    # 固定五段式结构
    structure_snapshot: StructureSnapshot = Field(..., description="Section 1: 结构快照")
    pattern_fitting: PatternFitting = Field(..., description="Section 2: 形态拟合")
    indicator_translate: IndicatorTranslate = Field(..., description="Section 3: 指标翻译")
    risk_of_misreading: MisreadingRisk = Field(..., description="Section 4: 误读风险")
    judgment_zone: JudgmentZone = Field(..., description="Section 5: 判断候选区")
    
    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "market_type": "A",
                "analysis_date": "2025-12-29T10:30:00",
                "structure_snapshot": {
                    "structure_type": "consolidation",
                    "ma200_position": "above",
                    "phase": "middle",
                    "key_levels": [
                        {"price": 12.50, "label": "近期支撑"},
                        {"price": 12.20, "label": "次级支撑"},
                        {"price": 13.00, "label": "近期压力"},
                        {"price": 13.50, "label": "前高压力"}
                    ],
                    "trend_description": "价格在MA200上方盘整，区间12.50-13.00，结构完整"
                },
                "pattern_fitting": {
                    "pattern_type": "triangle",
                    "pattern_description": "对称三角形整理，高点逐步降低，低点逐步抬升",
                    "completion_rate": 65
                },
                "indicator_translate": {
                    "indicators": [
                        {
                            "name": "RSI(14)",
                            "value": "52.3",
                            "signal": "neutral",
                            "interpretation": "RSI在中性区域，多空力量均衡"
                        },
                        {
                            "name": "MACD",
                            "value": "DIF: -0.05, DEA: -0.03",
                            "signal": "weakening",
                            "interpretation": "MACD在零轴下方收敛，动能减弱"
                        },
                        {
                            "name": "成交量",
                            "value": "0.8倍均量",
                            "signal": "weakening",
                            "interpretation": "成交量萎缩，观望情绪浓厚"
                        }
                    ],
                    "global_note": "指标整体显示盘整特征，缺乏方向性信号"
                },
                "risk_of_misreading": {
                    "risk_level": "medium",
                    "risk_factors": [
                        "三角形末端，方向选择临近",
                        "成交量持续萎缩，突破有效性存疑",
                        "大盘波动可能影响个股选择"
                    ],
                    "risk_flags": ["缩量", "窄幅震荡", "方向不明"],
                    "caution_note": "需等待有效突破确认，避免假突破陷阱"
                },
                "judgment_zone": {
                    "candidates": [
                        {
                            "option_id": "A",
                            "option_type": "structure_premise",
                            "description": "若有效突破13.00且放量，结构转为上升"
                        },
                        {
                            "option_id": "B",
                            "option_type": "structure_premise",
                            "description": "若跌破12.50且放量，结构转为下降"
                        },
                        {
                            "option_id": "C",
                            "option_type": "structure_premise",
                            "description": "继续在区间内震荡，等待方向明确"
                        }
                    ],
                    "risk_checks": [
                        "突破时成交量是否显著放大",
                        "突破后能否站稳关键位",
                        "大盘环境是否配合"
                    ],
                    "note": "以上为结构分析，非走势预测，系统不提供买卖建议"
                }
            }
        }
