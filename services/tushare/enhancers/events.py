"""
Events Enhancer
事件与复权提醒 + 财报披露日历
"""
from datetime import datetime, timedelta
from typing import List, Optional

from .base import BaseEnhancer
from ..schemas import ModuleResult, KeyMetric, ModuleDetails, TableData
from utils.logger import get_logger

logger = get_logger()

# 财报披露临近提醒窗口（天）
DISCLOSURE_ALERT_DAYS = 14


class EventsEnhancer(BaseEnhancer):
    """
    事件提醒增强器
    
    输出: event_count_30d, has_corporate_action, events_30d,
          days_to_disclosure（距最近财报披露日天数，无则为 None）
    """
    
    MODULE_NAME = "events"
    
    def enhance(self, ts_code: str, asof: str = None) -> ModuleResult:
        """获取近30日事件信息 + 财报披露日历"""
        if asof is None:
            asof = datetime.now().strftime('%Y-%m-%d')
        
        # 检查缓存
        hit, cached = self._get_cached(ts_code, asof.replace('-', ''))
        if hit and cached:
            return cached
        
        end_date = asof.replace('-', '')
        start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=30)).strftime('%Y%m%d')
        
        events = []
        has_corporate_action = False
        
        # 尝试获取分红送股信息
        try:
            dividend_df = self.client.query('dividend', ts_code=ts_code)
            if dividend_df is not None and len(dividend_df) > 0:
                # 筛选近30日的分红
                dividend_df['ex_date'] = dividend_df['ex_date'].astype(str)
                recent_div = dividend_df[
                    (dividend_df['ex_date'] >= start_date) & 
                    (dividend_df['ex_date'] <= end_date)
                ]
                for _, row in recent_div.iterrows():
                    events.append({
                        'date': row['ex_date'],
                        'type': '分红除权',
                        'title': f"除权除息日",
                        'impact_hint': '注意复权口径解读关键位'
                    })
                    has_corporate_action = True
        except Exception as e:
            logger.debug(f"[Events] Dividend query failed: {e}")
        
        # 财报披露日历（tushare disclosure_date，akshare 东财降级）
        days_to_disclosure: Optional[int] = None
        try:
            disclosure_events, days_to_disclosure = self._fetch_disclosure_events(
                ts_code, start_date=start_date, end_date=end_date
            )
            events.extend(disclosure_events)
        except Exception as e:
            logger.debug(f"[Events] Disclosure calendar failed: {e}")
        
        event_count = len(events)
        
        # 生成摘要
        summary_parts = []
        if days_to_disclosure is not None and 0 <= days_to_disclosure <= DISCLOSURE_ALERT_DAYS:
            summary_parts.append(
                f"距财报披露约 {days_to_disclosure} 天，事件窗口内波动可能放大"
            )
        if event_count > 0:
            summary_parts.append(f"近30日存在{event_count}个重要事件，注意复权口径解读")
        if not summary_parts:
            summary_parts.append("近30日无重大公司事件（分红/财报披露等）")
        summary = "；".join(summary_parts) + "。"
        
        key_metrics = [
            KeyMetric(key="event_count_30d", label="30日事件数", value=event_count, unit=None),
            KeyMetric(key="has_corporate_action", label="有公司行动", value=has_corporate_action, unit=None),
            KeyMetric(key="days_to_disclosure", label="距财报披露天数", value=days_to_disclosure, unit="天"),
        ]
        
        result = ModuleResult(
            available=True,
            degraded=event_count == 0 and days_to_disclosure is None,
            degrade_reason="部分事件接口需要更高权限" if (event_count == 0 and days_to_disclosure is None) else None,
            summary=summary,
            key_metrics=key_metrics,
            details=ModuleDetails(
                tables=[TableData(
                    name="events_30d",
                    columns=["date", "type", "title", "impact_hint"],
                    rows=events
                )] if events else [],
                notes=[
                    f"查询区间: {start_date} ~ {end_date}",
                    "事件包括: 分红除权、财报披露计划等",
                    "若存在除权事件，验证周期建议≥7天并以复权口径观察",
                    "财报披露窗口前后，价格波动可能与结构信号无关，注意区分",
                ]
            ),
            meta=self._make_meta(asof, cache_hit=False)
        )
        
        self._set_cache(ts_code, result, asof.replace('-', ''))
        return result

    def _fetch_disclosure_events(
        self, ts_code: str, *, start_date: str, end_date: str
    ) -> tuple:
        """
        获取财报披露事件。

        Returns:
            (events, days_to_disclosure)
            - events: 近30日已披露 + 未来 DISCLOSURE_ALERT_DAYS 天内预约披露
            - days_to_disclosure: 距最近一次未来预约披露的天数（无则 None）
        """
        events: List[dict] = []
        days_to_disclosure: Optional[int] = None

        df = self.client.query('disclosure_date', ts_code=ts_code)
        if df is None or len(df) == 0:
            return events, days_to_disclosure

        df = df.fillna('')
        today = datetime.strptime(end_date, '%Y%m%d')

        # 未来预约披露：actual_date 为空且 pre_date >= today
        pending = df[(df['actual_date'] == '') & (df['pre_date'] != '')]
        future_dates = sorted(
            d for d in pending['pre_date'].astype(str) if d >= end_date
        )
        if future_dates:
            next_date = future_dates[0]
            days_to_disclosure = (datetime.strptime(next_date, '%Y%m%d') - today).days
            if days_to_disclosure <= DISCLOSURE_ALERT_DAYS:
                report_period = self._report_period_label(
                    str(pending[pending['pre_date'] == next_date]['end_date'].iloc[0])
                )
                events.append({
                    'date': next_date,
                    'type': '财报披露',
                    'title': f"预约披露{report_period}",
                    'impact_hint': f"距披露约 {days_to_disclosure} 天，事件窗口波动可能放大",
                })

        # 近30日已实际披露
        disclosed = df[(df['actual_date'] != '')]
        recent = disclosed[
            (disclosed['actual_date'].astype(str) >= start_date)
            & (disclosed['actual_date'].astype(str) <= end_date)
        ]
        for _, row in recent.iterrows():
            report_period = self._report_period_label(str(row['end_date']))
            events.append({
                'date': str(row['actual_date']),
                'type': '财报披露',
                'title': f"已披露{report_period}",
                'impact_hint': '财报落地后注意结构是否被事件重新定价',
            })

        return events, days_to_disclosure

    @staticmethod
    def _report_period_label(end_date: str) -> str:
        """报告期转可读标签：20260630 -> 2026年中报"""
        if len(end_date) != 8:
            return "定期报告"
        year, md = end_date[:4], end_date[4:]
        period_map = {
            '0331': '一季报',
            '0630': '中报',
            '0930': '三季报',
            '1231': '年报',
        }
        label = period_map.get(md)
        return f"{year}年{label}" if label else f"{year}年定期报告"
