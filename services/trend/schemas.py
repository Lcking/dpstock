"""
Trend Schemas
趋势计算结果模型
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class TrendInput(BaseModel):
    """趋势计算输入"""
    close: float
    ma5: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ma200: Optional[float] = None
    ma200_prev20: Optional[float] = None  # 20日前的MA200
    ma200_prev5: Optional[float] = None   # 备用：5日前的MA200


class TrendResult(BaseModel):
    """
    趋势计算结果 (PRD Trend Spec T1-T6)
    
    必须包含: direction, strength(0-100), degraded, evidence[]
    """
    direction: Literal["up", "down", "sideways"]
    strength: int = Field(ge=0, le=100, description="趋势强度 0-100")
    degraded: bool = Field(default=False, description="数据降级标记")
    evidence: List[str] = Field(default_factory=list, description="证据列表 2-5条")
    
    # 内部派生量（可选输出，用于调试）
    _dist200: Optional[float] = None
    _slope200: Optional[float] = None
    _ma_stack: Optional[str] = None


class MAStack(str):
    """均线排列类型"""
    BULL_STACK = "BULL_STACK"           # ma5 > ma20 > ma60
    BEAR_STACK = "BEAR_STACK"           # ma5 < ma20 < ma60
    BULL_STACK_LITE = "BULL_STACK_LITE" # ma20 > ma60 (缺ma5)
    BEAR_STACK_LITE = "BEAR_STACK_LITE" # ma20 < ma60 (缺ma5)
    MIXED_STACK = "MIXED_STACK"         # 其他
