"""
Watchlist Schemas
自选股列表数据模型 - 按 PRD v1.3 定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

from services.trend.schemas import TrendResult


class IndustryExposureItem(BaseModel):
    """单行业暴露（等权假设：每只自选股权重相同）"""
    industry: str
    count: int = Field(ge=0)
    weight_pct: float = Field(ge=0, le=100)


class RiskListHitItem(BaseModel):
    """自选标的命中当日风险股清单"""
    ts_code: str
    name: str
    trade_date: str
    tags: List[str] = Field(default_factory=list)
    risk_level: str = "high"
    reason: str = ""


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
    weight_pct: Optional[float] = Field(None, ge=0, le=100, description="用户设定持仓权重%")
    is_skeleton: bool = False
    on_risk_list: bool = False
    risk_list_tags: List[str] = Field(default_factory=list)


class WatchlistHealthOverview(BaseModel):
    """自选股整体健康度概览"""
    total_count: int = 0
    strong_count: int = 0
    weak_count: int = 0
    high_risk_count: int = 0
    watch_count: int = 0
    active_judgment_count: int = 0
    health_score: int = Field(0, ge=0, le=100)
    label: Literal["偏强", "均衡", "偏弱", "风险偏高"] = "均衡"
    summary_line: str = ""
    industry_count: int = 0
    top_industries: List[IndustryExposureItem] = Field(default_factory=list)
    concentration_level: Literal["分散", "中等", "偏高"] = "分散"
    concentration_note: str = ""
    uses_position_weights: bool = False
    risk_list_hits: List[RiskListHitItem] = Field(default_factory=list)
    risk_list_trade_date: Optional[str] = None


class Watchlist(BaseModel):
    """自选股列表"""
    id: str
    user_id: str
    name: str
    created_at: datetime
    updated_at: datetime
    items_count: int = 0
    is_temporary: bool = False
    trial_message: Optional[str] = None


class WatchlistCreate(BaseModel):
    """创建自选股列表请求"""
    name: str = Field(default="默认自选", max_length=50)


class WatchlistUpdate(BaseModel):
    """更新自选股列表请求"""
    name: Optional[str] = Field(None, max_length=50)


class WatchlistAddSymbols(BaseModel):
    """添加标的请求"""
    ts_codes: List[str] = Field(..., min_length=1, max_length=50)


class WatchlistSymbolWeightUpdate(BaseModel):
    """更新单只标的持仓权重（百分比，留空表示恢复等权）"""
    weight_pct: Optional[float] = Field(None, ge=0, le=100)


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
    health_overview: WatchlistHealthOverview = Field(default_factory=WatchlistHealthOverview)
    is_temporary: bool = False
    trial_message: Optional[str] = None
