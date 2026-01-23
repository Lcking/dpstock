"""
Compare Bucketing Service
比较分桶服务 - PRD 2.3 四桶看板逻辑
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from schemas.watchlist import WatchlistItemSummary
from services.watchlist import watchlist_service
from services.tushare.orchestrator import enhancement_orchestrator
from utils.logger import get_logger

logger = get_logger()


@dataclass
class Bucket:
    """分桶结构"""
    id: str
    title: str
    reason: str
    items: List[WatchlistItemSummary]


@dataclass
class CompareResult:
    """比较结果"""
    meta: Dict
    buckets: List[Bucket]


class CompareBucketingService:
    """
    比较分桶服务
    
    PRD 2.3 四桶规则:
    - event: E == major
    - best: T==up AND R∈{strong,neutral} AND F∈{positive,neutral}
    - weak: T==down AND (R==weak OR F==negative)
    - conflict: 其余全部
    """
    
    BUCKET_DEFINITIONS = {
        "event": {
            "title": "事件扰动",
            "reason": "近30日存在重大事件/复权扰动，建议延长验证周期"
        },
        "best": {
            "title": "结构占优",
            "reason": "趋势与相对强弱一致，资金不拖后腿"
        },
        "weak": {
            "title": "结构偏弱",
            "reason": "趋势偏弱且相对强弱或资金为负"
        },
        "conflict": {
            "title": "信号冲突",
            "reason": "趋势/强弱/资金出现矛盾，建议先验证前提"
        }
    }
    
    # Flow label 映射到信号
    FLOW_SIGNAL_MAP = {
        "承接放量": "positive",
        "缩量潜伏": "neutral",
        "中性": "neutral",
        "缩量观望": "neutral",
        "分歧放量": "negative",
        "缩量阴跌": "negative",
        "不可用": "unavailable"
    }
    
    def compare(
        self,
        ts_codes: List[str],
        asof: Optional[str] = None,
        window: int = 20,
        bench: str = "000300.SH",
        use_industry: bool = True
    ) -> CompareResult:
        """
        执行比较分桶
        
        Args:
            ts_codes: 股票代码列表 (3-10只)
            asof: 日期
            window: 窗口期
            bench: 基准指数
            use_industry: 是否使用行业基准
        
        Returns:
            CompareResult with 4 buckets
        """
        if asof is None:
            asof = datetime.now().strftime('%Y-%m-%d')
        
        # 生成所有标的的摘要
        summaries = []
        for ts_code in ts_codes:
            try:
                summary = watchlist_service._generate_single_summary(ts_code, asof)
                summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to generate summary for {ts_code}: {e}")
                summaries.append(watchlist_service._degraded_summary(ts_code, asof))
        
        # 分桶
        buckets = self._bucket_summaries(summaries)
        
        return CompareResult(
            meta={
                "asof": asof,
                "window": window,
                "bench": bench,
                "use_industry": use_industry,
                "total_count": len(ts_codes)
            },
            buckets=buckets
        )
    
    def _bucket_summaries(
        self, 
        summaries: List[WatchlistItemSummary]
    ) -> List[Bucket]:
        """按规则分桶"""
        buckets = {
            "event": [],
            "best": [],
            "weak": [],
            "conflict": []
        }
        
        for summary in summaries:
            bucket_id = self._determine_bucket(summary)
            buckets[bucket_id].append(summary)
        
        # 按结构评分排序每个桶内的标的
        for bucket_id in buckets:
            buckets[bucket_id].sort(
                key=lambda s: watchlist_service._calc_structure_score(s),
                reverse=True
            )
        
        # 构建返回结果 (固定顺序: best, conflict, weak, event)
        result = []
        for bucket_id in ["best", "conflict", "weak", "event"]:
            bucket_def = self.BUCKET_DEFINITIONS[bucket_id]
            result.append(Bucket(
                id=bucket_id,
                title=bucket_def["title"],
                reason=bucket_def["reason"],
                items=buckets[bucket_id]
            ))
        
        return result
    
    def _determine_bucket(self, summary: WatchlistItemSummary) -> str:
        """
        判定标的所属桶
        
        决策树（优先级固定）：
        1. event: E == major
        2. best: T==up AND R∈{strong,neutral} AND F∈{positive,neutral}
        3. weak: T==down AND (R==weak OR F==negative)
        4. conflict: 其余全部
        """
        # 提取信号
        T = summary.trend.direction  # up/down/sideways
        R = summary.relative_strength.label_20d  # strong/neutral/weak/None
        E = summary.events.flag  # none/minor/major/unavailable
        
        # Flow 信号映射
        flow_label = summary.capital_flow.label
        F = self.FLOW_SIGNAL_MAP.get(flow_label, "neutral")
        
        # 1. 事件扰动 (最高优先级)
        if E == "major":
            return "event"
        
        # 2. 结构占优
        if (T == "up" and 
            R in ("strong", "neutral", None) and 
            F in ("positive", "neutral")):
            return "best"
        
        # 3. 结构偏弱
        if T == "down" and (R == "weak" or F == "negative"):
            return "weak"
        
        # 4. 信号冲突 (默认)
        return "conflict"
    
    def calc_structure_score(self, summary: WatchlistItemSummary) -> int:
        """
        计算结构评分 (0-100, 用于排序)
        
        PRD 2.4:
        Trend: up +30 / sideways +15 / down +0
        RS: strong +30 / neutral +15 / weak +0
        Flow: positive +20 / neutral +10 / negative +0 / unavailable +5
        Risk: low +20 / medium +10 / high +0
        Event: major -30 / minor -10 / none 0 / unavailable -5
        """
        return watchlist_service._calc_structure_score(summary)


# 单例
compare_service = CompareBucketingService()
