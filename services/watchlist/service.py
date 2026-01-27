"""
Watchlist Service
自选股列表服务 - 核心业务逻辑
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from database.db_factory import DatabaseFactory
from schemas.watchlist import (
    Watchlist, WatchlistCreate, WatchlistItemSummary,
    RelativeStrengthSummary, CapitalFlowSummary, RiskSummary,
    EventSummary, JudgementSummary, WatchlistSummaryResponse
)
from services.trend import trend_calculator, TrendInput, TrendResult
from services.tushare.orchestrator import enhancement_orchestrator
from utils.logger import get_logger

logger = get_logger()


class WatchlistService:
    """
    自选股列表服务
    
    职责:
    - CRUD 操作
    - 批量摘要生成 (避免逐只拉取风暴)
    - 排序与筛选
    """
    
    def __init__(self):
        self.db = DatabaseFactory()
    
    # ========== CRUD ==========
    
    def create_watchlist(self, user_id: str, data: WatchlistCreate) -> Watchlist:
        """创建自选股列表"""
        now = datetime.utcnow().isoformat() + 'Z'
        watchlist_id = f"wl_{uuid.uuid4().hex[:12]}"
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO watchlists (id, user_id, name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (watchlist_id, user_id, data.name, now, now))
            conn.commit()
        
        return Watchlist(
            id=watchlist_id,
            user_id=user_id,
            name=data.name,
            created_at=datetime.fromisoformat(now.replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(now.replace('Z', '+00:00')),
            items_count=0
        )
    
    def get_user_watchlists(self, user_id: str) -> List[Watchlist]:
        """获取用户的所有自选股列表"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT w.id, w.user_id, w.name, w.created_at, w.updated_at,
                       (SELECT COUNT(*) FROM watchlist_items WHERE watchlist_id = w.id) as items_count
                FROM watchlists w
                WHERE w.user_id = ?
                ORDER BY w.created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
        
        return [
            Watchlist(
                id=row.get('id'),
                user_id=row.get('user_id'),
                name=row.get('name'),
                created_at=datetime.fromisoformat(row.get('created_at', '').replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(row.get('updated_at', '').replace('Z', '+00:00')),
                items_count=row.get('items_count', 0)
            )
            for row in rows
        ]
    
    def add_symbols(self, watchlist_id: str, ts_codes: List[str]) -> int:
        """添加标的到自选股列表"""
        now = datetime.utcnow().isoformat() + 'Z'
        added = 0
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for ts_code in ts_codes:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO watchlist_items (watchlist_id, ts_code, added_at)
                        VALUES (?, ?, ?)
                    """, (watchlist_id, ts_code, now))
                    if cursor.rowcount > 0:
                        added += 1
                except Exception as e:
                    logger.warning(f"Failed to add {ts_code}: {e}")
            
            # 更新列表的 updated_at
            cursor.execute("""
                UPDATE watchlists SET updated_at = ? WHERE id = ?
            """, (now, watchlist_id))
            conn.commit()
        
        return added
    
    def remove_symbol(self, watchlist_id: str, ts_code: str) -> bool:
        """从自选股列表移除标的"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM watchlist_items
                WHERE watchlist_id = ? AND ts_code = ?
            """, (watchlist_id, ts_code))
            
            removed = cursor.rowcount > 0
            
            if removed:
                now = datetime.utcnow().isoformat() + 'Z'
                cursor.execute("""
                    UPDATE watchlists SET updated_at = ? WHERE id = ?
                """, (now, watchlist_id))
            
            conn.commit()
        
        return removed
    
    def get_watchlist_items(self, watchlist_id: str) -> List[str]:
        """获取自选股列表中的所有标的代码"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ts_code FROM watchlist_items
                WHERE watchlist_id = ?
                ORDER BY added_at DESC
            """, (watchlist_id,))
            rows = cursor.fetchall()
        
        return [row.get('ts_code') for row in rows]
    
    # ========== 批量摘要 ==========
    
    def get_summary(
        self,
        watchlist_id: str,
        asof: Optional[str] = None,
        sort: str = "SCORE_DESC",
        filters: Optional[List[str]] = None
    ) -> WatchlistSummaryResponse:
        """
        获取批量摘要 (核心接口)
        
        PRD 强制: 必须批量返回，避免逐只触发 analysis 风暴
        """
        if asof is None:
            asof = datetime.now().strftime('%Y-%m-%d')
        
        # 获取标的列表
        ts_codes = self.get_watchlist_items(watchlist_id)
        
        if not ts_codes:
            return WatchlistSummaryResponse(
                watchlist_id=watchlist_id,
                asof=asof,
                items=[],
                total_count=0,
                filtered_count=0
            )
        
        # 批量生成摘要
        summaries = self._batch_generate_summaries(ts_codes, asof)
        
        # 应用过滤
        filtered = self._apply_filters(summaries, filters or [])
        
        # 应用排序
        sorted_items = self._apply_sort(filtered, sort)
        
        return WatchlistSummaryResponse(
            watchlist_id=watchlist_id,
            asof=asof,
            items=sorted_items,
            total_count=len(ts_codes),
            filtered_count=len(sorted_items)
        )
    
    def _batch_generate_summaries(
        self, 
        ts_codes: List[str], 
        asof: str
    ) -> List[WatchlistItemSummary]:
        """批量生成摘要"""
        summaries = []
        
        for ts_code in ts_codes:
            try:
                summary = self._generate_single_summary(ts_code, asof)
                summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to generate summary for {ts_code}: {e}")
                # 降级摘要
                summaries.append(self._degraded_summary(ts_code, asof))
        
        return summaries
    
    def _generate_single_summary(
        self, 
        ts_code: str, 
        asof: str
    ) -> WatchlistItemSummary:
        """生成单个标的摘要（带缓存）"""
        from .cache import watchlist_summary_cache
        
        # Check cache first
        cached = watchlist_summary_cache.get(ts_code, asof)
        if cached is not None:
            logger.debug(f"[Watchlist] Cache HIT for {ts_code}")
            return cached
        
        logger.debug(f"[Watchlist] Cache MISS for {ts_code}, generating...")
        
        # 获取增强数据
        enhancements = enhancement_orchestrator.enhance(ts_code, asof)
        
        # 提取各模块数据
        rs_data = enhancements.relative_strength
        flow_data = enhancements.capital_flow
        events_data = enhancements.events
        
        # 构建 Trend (需要从数据源获取MA数据)
        trend = self._build_trend(ts_code, asof)
        
        # 构建 RelativeStrength
        relative_strength = self._build_rs_summary(rs_data)
        
        # 构建 CapitalFlow
        capital_flow = self._build_flow_summary(flow_data)
        
        # 构建 Risk
        risk = self._build_risk_summary(rs_data, flow_data)
        
        # 构建 Events
        events = self._build_events_summary(events_data)
        
        # 构建 Judgement (从判断记录)
        judgement = self._get_judgement_status(ts_code)
        
        # 获取价格信息
        price, change_pct, name = self._get_price_info(ts_code, asof)
        
        summary = WatchlistItemSummary(
            ts_code=ts_code,
            name=name or ts_code,
            asof=asof,
            price=price,
            change_pct=change_pct,
            trend=trend,
            relative_strength=relative_strength,
            capital_flow=capital_flow,
            risk=risk,
            events=events,
            judgement=judgement
        )
        
        # Store in cache
        watchlist_summary_cache.set(ts_code, asof, summary)
        
        return summary
    
    def _build_trend(self, ts_code: str, asof: str) -> TrendResult:
        """构建趋势数据"""
        # TODO: 从股票数据服务获取MA数据
        # 暂时返回降级结果
        try:
            from services.tushare.client import tushare_client
            from datetime import timedelta
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=400) # 获取足够多的数据以计算MA200
            
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            
            # 获取日线数据
            df = tushare_client.get_daily(ts_code, start_date=start_str, end_date=end_str)
            
            if df is None or df.empty:
                return TrendResult(
                    direction="sideways",
                    strength=0,
                    degraded=True,
                    evidence=["无法获取行情数据"]
                )
            
            # Tushare 返回的数据通常是倒序的 (最新在前)，需要反转为时间正序以计算 rolling
            df = df.sort_values('trade_date')
            
            # 计算MA
            df['ma5'] = df['close'].rolling(5).mean()
            df['ma20'] = df['close'].rolling(20).mean()
            df['ma60'] = df['close'].rolling(60).mean()
            df['ma200'] = df['close'].rolling(200).mean()
            
            latest = df.iloc[-1]
            prev20 = df.iloc[-21] if len(df) > 20 else None
            
            input_data = TrendInput(
                close=latest['close'],
                ma5=latest.get('ma5'),
                ma20=latest.get('ma20'),
                ma60=latest.get('ma60'),
                ma200=latest.get('ma200'),
                ma200_prev20=prev20['ma200'] if prev20 is not None and 'ma200' in prev20 else None
            )
            
            return trend_calculator.calculate(input_data)
            
        except Exception as e:
            logger.error(f"Error building trend for {ts_code}: {e}")
            return TrendResult(
                direction="sideways",
                strength=0,
                degraded=True,
                evidence=["趋势计算失败"]
            )
    
    def _build_rs_summary(self, rs_data) -> RelativeStrengthSummary:
        """构建相对强弱摘要"""
        if rs_data is None or not rs_data.available:
            return RelativeStrengthSummary(
                excess_20d_vs_000300=None,
                label_20d=None,
                bench="000300.SH"
            )
        
        # 从 key_metrics 提取
        excess_20d = None
        for m in rs_data.key_metrics or []:
            if m.key == 'excess_20d':
                excess_20d = m.value / 100 if m.value else None  # 转换为小数
        
        # 判断 label
        label = None
        if excess_20d is not None:
            if excess_20d >= 0.015:
                label = "strong"
            elif excess_20d <= -0.015:
                label = "weak"
            else:
                label = "neutral"
        
        return RelativeStrengthSummary(
            excess_20d_vs_000300=excess_20d,
            label_20d=label,
            bench="000300.SH"
        )
    
    def _build_flow_summary(self, flow_data) -> CapitalFlowSummary:
        """构建资金流向摘要"""
        if flow_data is None or not flow_data.available:
            return CapitalFlowSummary(
                label="不可用",
                net_inflow_5d=None,
                available=False,
                degraded=True
            )
        
        # 从 key_metrics 提取
        label = "中性"
        net_5d = None
        
        for m in flow_data.key_metrics or []:
            if m.key == 'flow_label':
                label = m.value or "中性"
            elif m.key == 'net_inflow_5d':
                net_5d = m.value * 100000000 if m.value else None  # 亿转元
        
        return CapitalFlowSummary(
            label=label,
            net_inflow_5d=net_5d,
            available=True,
            degraded=flow_data.degraded
        )
    
    def _build_risk_summary(self, rs_data, flow_data) -> RiskSummary:
        """构建风险摘要"""
        # 简单规则: 弱势 + 资金流出 = high, 强势 + 资金流入 = low
        level = "medium"
        
        rs_weak = False
        flow_negative = False
        
        if rs_data and rs_data.available:
            for m in rs_data.key_metrics or []:
                if m.key == 'excess_20d' and m.value is not None:
                    if m.value <= -3:
                        rs_weak = True
        
        if flow_data and flow_data.available:
            for m in flow_data.key_metrics or []:
                if m.key == 'flow_label':
                    if m.value in ('分歧放量', '缩量阴跌'):
                        flow_negative = True
        
        if rs_weak and flow_negative:
            level = "high"
        elif not rs_weak and not flow_negative:
            level = "low"
        
        return RiskSummary(level=level, vol_percentile=None)
    
    def _build_events_summary(self, events_data) -> EventSummary:
        """构建事件摘要"""
        if events_data is None or not events_data.available:
            return EventSummary(
                flag="unavailable",
                event_count_30d=0,
                available=False
            )
        
        count = 0
        has_action = False
        
        for m in events_data.key_metrics or []:
            if m.key == 'event_count_30d':
                count = m.value or 0
            elif m.key == 'has_corporate_action':
                has_action = bool(m.value)
        
        if has_action:
            flag = "major"
        elif count > 0:
            flag = "minor"
        else:
            flag = "none"
        
        return EventSummary(
            flag=flag,
            event_count_30d=count,
            available=True
        )
    
    def _get_judgement_status(self, ts_code: str) -> JudgementSummary:
        """获取判断状态"""
        # 从判断记录中查询活跃判断
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT candidate, validation_date, status
                    FROM judgments
                    WHERE stock_code = ? AND status IN ('active', 'pending')
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (ts_code,))
                row = cursor.fetchone()
            
            if row:
                validation_date = row.get('validation_date')
                days_left = None
                if validation_date:
                    try:
                        val_dt = datetime.fromisoformat(validation_date.replace('Z', '+00:00'))
                        days_left = (val_dt - datetime.now()).days
                        if days_left < 0:
                            days_left = 0
                    except:
                        pass
                
                return JudgementSummary(
                    has_active=True,
                    candidate=row.get('candidate'),
                    validation_period_days=7,  # 默认7天
                    days_left=days_left
                )
        except Exception as e:
            logger.debug(f"Error getting judgement status for {ts_code}: {e}")
        
        return JudgementSummary(has_active=False)
    
    def _get_price_info(self, ts_code: str, asof: str):
        """获取价格信息"""
        try:
            from services.tushare.client import tushare_client
            df = tushare_client.daily(ts_code, days=5)
            
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return (
                    latest['close'],
                    latest.get('pct_chg', 0) / 100 if 'pct_chg' in latest else None,
                    None  # TODO: 获取名称
                )
        except:
            pass
        
        return 0.0, None, None
    
    def _degraded_summary(self, ts_code: str, asof: str) -> WatchlistItemSummary:
        """降级摘要"""
        return WatchlistItemSummary(
            ts_code=ts_code,
            name=ts_code,
            asof=asof,
            price=0.0,
            change_pct=None,
            trend=TrendResult(
                direction="sideways",
                strength=0,
                degraded=True,
                evidence=["数据获取失败"]
            ),
            relative_strength=RelativeStrengthSummary(),
            capital_flow=CapitalFlowSummary(label="不可用", available=False, degraded=True),
            risk=RiskSummary(level="medium"),
            events=EventSummary(flag="unavailable", available=False),
            judgement=JudgementSummary()
        )
    
    def _apply_filters(
        self, 
        summaries: List[WatchlistItemSummary],
        filters: List[str]
    ) -> List[WatchlistItemSummary]:
        """应用过滤条件"""
        result = summaries
        
        for f in filters:
            if f == "STRUCTURE_ADVANTAGE":
                result = [s for s in result if s.trend.direction == "up"]
            elif f == "NO_EVENT":
                result = [s for s in result if s.events.flag == "none"]
            elif f == "HAS_JUDGEMENT":
                result = [s for s in result if s.judgement.has_active]
            elif f == "LOW_RISK":
                result = [s for s in result if s.risk.level == "low"]
            elif f == "STRONG_RS":
                result = [s for s in result if s.relative_strength.label_20d == "strong"]
        
        return result
    
    def _apply_sort(
        self, 
        summaries: List[WatchlistItemSummary],
        sort: str
    ) -> List[WatchlistItemSummary]:
        """应用排序"""
        if sort == "SCORE_DESC":
            return sorted(summaries, key=lambda s: self._calc_structure_score(s), reverse=True)
        elif sort == "RS_20D_DESC":
            return sorted(summaries, key=lambda s: s.relative_strength.excess_20d_vs_000300 or -999, reverse=True)
        elif sort == "TREND_STRENGTH_DESC":
            return sorted(summaries, key=lambda s: s.trend.strength, reverse=True)
        elif sort == "RISK_ASC":
            risk_order = {"low": 0, "medium": 1, "high": 2}
            return sorted(summaries, key=lambda s: risk_order.get(s.risk.level, 1))
        elif sort == "JUDGEMENT_DUE_SOON":
            return sorted(summaries, key=lambda s: s.judgement.days_left if s.judgement.days_left is not None else 999)
        
        return summaries
    
    def _calc_structure_score(self, summary: WatchlistItemSummary) -> int:
        """
        计算结构评分 (0-100, 仅用于排序)
        
        PRD 2.4:
        Trend: up +30 / sideways +15 / down +0
        RS: strong +30 / neutral +15 / weak +0
        Flow: positive +20 / neutral +10 / negative +0 / unavailable +5
        Risk: low +20 / medium +10 / high +0
        Event: major -30 / minor -10 / none 0 / unavailable -5
        """
        score = 0
        
        # Trend
        trend_scores = {"up": 30, "sideways": 15, "down": 0}
        score += trend_scores.get(summary.trend.direction, 15)
        
        # RS
        rs_scores = {"strong": 30, "neutral": 15, "weak": 0}
        score += rs_scores.get(summary.relative_strength.label_20d or "neutral", 15)
        
        # Flow
        flow_label = summary.capital_flow.label
        if flow_label == "承接放量":
            score += 20
        elif flow_label in ("中性", "缩量潜伏"):
            score += 10
        elif flow_label in ("分歧放量", "缩量阴跌"):
            score += 0
        elif flow_label == "不可用":
            score += 5
        else:
            score += 10
        
        # Risk
        risk_scores = {"low": 20, "medium": 10, "high": 0}
        score += risk_scores.get(summary.risk.level, 10)
        
        # Event
        event_scores = {"none": 0, "minor": -10, "major": -30, "unavailable": -5}
        score += event_scores.get(summary.events.flag, 0)
        
        return max(0, min(100, score))


# 单例
watchlist_service = WatchlistService()
