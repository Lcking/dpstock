"""
Tushare Enhancement Schemas
Pydantic models for structured enhancement data
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EvidenceDomain(str, Enum):
    """证据域"""
    PRICE = "PRICE"         # 价格/均线/关键位
    RELATIVE = "RELATIVE"   # 相对强弱
    FLOW = "FLOW"           # 资金流向
    EVENT = "EVENT"         # 事件/公告


class KeyMetric(BaseModel):
    """关键指标项"""
    key: str = Field(..., description="指标键名")
    label: str = Field(..., description="显示标签")
    value: Any = Field(..., description="指标值")
    unit: Optional[str] = Field(None, description="单位，如 'pct', 'yuan'")


class TableData(BaseModel):
    """表格数据"""
    name: str = Field(..., description="表名")
    columns: List[str] = Field(..., description="列名列表")
    rows: List[Dict[str, Any]] = Field(..., description="数据行")


class ModuleDetails(BaseModel):
    """模块详情"""
    tables: List[TableData] = Field(default_factory=list, description="数据表")
    notes: List[str] = Field(default_factory=list, description="口径说明")


class CacheInfo(BaseModel):
    """缓存信息"""
    hit: bool = Field(..., description="是否命中缓存")
    ttl_sec: int = Field(..., description="TTL 秒数")


class ModuleMeta(BaseModel):
    """模块元数据"""
    data_source: str = Field(default="tushare", description="数据来源")
    asof: str = Field(..., description="数据日期 YYYY-MM-DD")
    window_days: Optional[List[int]] = Field(None, description="窗口天数列表")
    benchmarks: Optional[List[str]] = Field(None, description="对照标的")
    calculation: Optional[str] = Field(None, description="计算口径说明")
    cache: Optional[CacheInfo] = Field(None, description="缓存信息")


class ModuleResult(BaseModel):
    """
    通用模块结果（所有增强模块必须遵循）
    
    强制：即使不可用，也要返回模块对象（available=false）
    """
    available: bool = Field(True, description="模块是否可用")
    degraded: bool = Field(False, description="是否降级（部分数据缺失）")
    degrade_reason: Optional[str] = Field(None, description="降级原因")
    summary: str = Field(..., description="一句话结论（<=80字）")
    key_metrics: List[KeyMetric] = Field(default_factory=list, description="关键指标列表")
    details: Optional[ModuleDetails] = Field(None, description="详情数据")
    meta: Optional[ModuleMeta] = Field(None, description="元数据")
    
    @classmethod
    def unavailable(cls, reason: str) -> 'ModuleResult':
        """创建不可用的模块结果"""
        return cls(
            available=False,
            degraded=False,
            degrade_reason=reason,
            summary=f"数据不可用: {reason}",
            key_metrics=[],
            details=None,
            meta=None
        )
    
    @classmethod
    def degraded_result(cls, reason: str, summary: str, **kwargs) -> 'ModuleResult':
        """创建降级的模块结果"""
        return cls(
            available=True,
            degraded=True,
            degrade_reason=reason,
            summary=summary,
            **kwargs
        )


class EnhancementsResponse(BaseModel):
    """
    顶层增强数据结构
    """
    version: str = Field(default="1.0.0", description="Schema 版本")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")
    available_modules: List[str] = Field(default_factory=list, description="可用模块列表")
    
    # P0 模块
    relative_strength: Optional[ModuleResult] = Field(None, description="相对强弱")
    industry_position: Optional[ModuleResult] = Field(None, description="行业位置")
    capital_flow: Optional[ModuleResult] = Field(None, description="资金流向")
    events: Optional[ModuleResult] = Field(None, description="事件提醒")
    
    # P1 模块（可选）
    market_structure: Optional[ModuleResult] = Field(None, description="市场结构")
    valuation: Optional[ModuleResult] = Field(None, description="估值快照")


# ============ Judgment Zone v1.1 增强 ============

class EnhancedPremise(BaseModel):
    """增强前提（用于判断区）"""
    id: str = Field(..., description="前提ID，如 'A_REL_RS_IMPROVE'")
    domain: EvidenceDomain = Field(..., description="证据域")
    text: str = Field(..., description="前提描述文本")
    binding: Optional[Dict[str, str]] = Field(None, description="绑定的模块和指标")
    available: bool = Field(True, description="前提是否可用")


class RiskCheckItem(BaseModel):
    """风险检查项"""
    id: str = Field(..., description="检查项ID")
    domain: EvidenceDomain = Field(..., description="证据域")
    text: str = Field(..., description="检查项描述")
    available: bool = Field(True, description="是否可用")


class JudgmentCandidate(BaseModel):
    """判断候选项（带增强前提）"""
    id: str = Field(..., description="选项ID，如 'A', 'B', 'C'")
    text: str = Field(..., description="原有判断文案")
    enhanced_premises: List[EnhancedPremise] = Field(default_factory=list, description="增强前提列表")


class JudgmentZoneV11(BaseModel):
    """判断区 v1.1（带增强）"""
    version: str = Field(default="1.1.0", description="版本")
    candidates: List[JudgmentCandidate] = Field(..., description="判断候选项")
    risk_checks: List[RiskCheckItem] = Field(..., description="风险检查项")
    recommended_risk_checks: List[str] = Field(default_factory=list, description="推荐的检查项ID")
    validation_period_options: List[int] = Field(default=[1, 3, 7, 30], description="验证周期选项")
    defaults: Dict[str, Any] = Field(default_factory=dict, description="默认值")
