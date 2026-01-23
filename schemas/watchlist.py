"""
Watchlist Schemas
自选股列表数据模型 - 按 PRD v1.3 定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

from services.trend.schemas import TrendResult


class RelativeStrengthSummary(BaseModel):
    """相对强弱摘要 (RS)"""
    excess_20d_vs_000300: Optional[float] = Field(None, description="20日超额收益 vs 沪深300")
    label_20d: Optional[Literal["strong", "neutral", "weak"]] = None
    bench: str = "000300.SH"


class CapitalFlowSummary(BaseModel):
    """资金流向摘要"""
    label: Literal["承接放量", "分歧放量", "中性", "缩量观望", "缩量潜伏", "缩量阴跌", "不可用"]
    net_inflow_5d: Optional[float] = Field(None, description="5日净流入(元)")
    available: bool = True
    degraded: bool = False


class RiskSummary(BaseModel):
    """风险状态摘要"""
    level: Literal["low", "medium", "high"]
    vol_percentile: Optional[int] = Field(None, ge=0, le=100, description="波动率百分位")


class EventSummary(BaseModel):
    """事件状态摘要"""
    flag: Literal["none", "minor", "major", "unavailable"]
    event_count_30d: int = 0
    available: bool = True


class JudgementSummary(BaseModel):
    """判断状态摘要"""
    has_active: bool = False
    candidate: Optional[Literal["A", "B", "C"]] = None
    validation_period_days: Optional[int] = None
    days_left: Optional[int] = None


class WatchlistItemSummary(BaseModel):
    """
    自选股摘要 - PRD 1.3 核心契约
    
    6个必须字段:
    1. trend - 趋势状态
    2. relative_strength - 相对强弱
    3. capital_flow - 资金语言
    4. risk - 风险状态
    5. events - 事件状态
    6. judgement - 判断状态
    """
    ts_code: str
    name: str
    asof: str  # YYYY-MM-DD
    price: float
    change_pct: Optional[float] = None
    
    # 6个必须字段
    trend: TrendResult
    relative_strength: RelativeStrengthSummary
    capital_flow: CapitalFlowSummary
    risk: RiskSummary
    events: EventSummary
    judgement: JudgementSummary


class Watchlist(BaseModel):
    """自选股列表"""
    id: str
    user_id: str
    name: str
    created_at: datetime
    updated_at: datetime
    items_count: int = 0


class WatchlistCreate(BaseModel):
    """创建自选股列表请求"""
    name: str = Field(default="默认自选", max_length=50)


class WatchlistUpdate(BaseModel):
    """更新自选股列表请求"""
    name: Optional[str] = Field(None, max_length=50)


class WatchlistAddSymbols(BaseModel):
    """添加标的请求"""
    ts_codes: List[str] = Field(..., min_length=1, max_length=50)


class WatchlistSummaryRequest(BaseModel):
    """获取摘要请求"""
    asof: Optional[str] = None  # YYYY-MM-DD
    sort: Optional[str] = "SCORE_DESC"  # 排序方式
    filters: Optional[List[str]] = None  # 过滤条件


class WatchlistSummaryResponse(BaseModel):
    """摘要响应"""
    watchlist_id: str
    asof: str
    items: List[WatchlistItemSummary]
    total_count: int
    filtered_count: int
