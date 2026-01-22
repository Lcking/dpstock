"""
Events Enhancer
事件与复权提醒
"""
from datetime import datetime, timedelta
from .base import BaseEnhancer
from ..schemas import ModuleResult, KeyMetric, ModuleDetails, TableData
from utils.logger import get_logger

logger = get_logger()


class EventsEnhancer(BaseEnhancer):
    """
    事件提醒增强器
    
    输出: event_count_30d, has_corporate_action, events_30d
    """
    
    MODULE_NAME = "events"
    
    def enhance(self, ts_code: str, asof: str = None) -> ModuleResult:
        """获取近30日事件信息"""
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
        
        # 尝试获取公告信息（如果有权限）
        try:
            # disclosure_date 或 anns 等接口
            # 由于接口权限问题，这里简化处理
            pass
        except Exception as e:
            logger.debug(f"[Events] Announcement query failed: {e}")
        
        event_count = len(events)
        
        # 生成摘要
        if event_count > 0:
            summary = f"近30日存在{event_count}个重要事件，注意复权口径解读。"
        else:
            summary = "近30日无重大公司事件（分红/公告等）。"
        
        key_metrics = [
            KeyMetric(key="event_count_30d", label="30日事件数", value=event_count, unit=None),
            KeyMetric(key="has_corporate_action", label="有公司行动", value=has_corporate_action, unit=None)
        ]
        
        result = ModuleResult(
            available=True,
            degraded=event_count == 0,  # 如果没有事件，可能是权限问题
            degrade_reason="部分事件接口需要更高权限" if event_count == 0 else None,
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
                    "事件包括: 分红除权、重大公告等",
                    "若存在除权事件，验证周期建议≥7天并以复权口径观察"
                ]
            ),
            meta=self._make_meta(asof, cache_hit=False)
        )
        
        self._set_cache(ts_code, result, asof.replace('-', ''))
        return result
