"""EventsEnhancer 财报披露日历。"""
from datetime import datetime, timedelta

import pandas as pd

from services.tushare.enhancers.events import EventsEnhancer, DISCLOSURE_ALERT_DAYS


class FakeClient:
    """模拟 tushare client：只回应 dividend / disclosure_date。"""

    is_available = True

    def __init__(self, disclosure_df=None, dividend_df=None):
        self._disclosure_df = disclosure_df
        self._dividend_df = dividend_df

    def query(self, api_name, **kwargs):
        if api_name == 'disclosure_date':
            return self._disclosure_df
        if api_name == 'dividend':
            return self._dividend_df
        return None


class NoCache:
    TTL_CONFIG = {}

    def get(self, *args, **kwargs):
        return False, None

    def set(self, *args, **kwargs):
        pass


def _make_enhancer(disclosure_df=None, dividend_df=None) -> EventsEnhancer:
    enh = EventsEnhancer()
    enh.client = FakeClient(disclosure_df, dividend_df)
    enh.cache = NoCache()
    return enh


def test_upcoming_disclosure_within_window_creates_event_and_metric():
    today = datetime.now()
    pre_date = (today + timedelta(days=7)).strftime('%Y%m%d')
    df = pd.DataFrame([
        {'ts_code': '600519.SH', 'ann_date': '', 'end_date': '20260630',
         'pre_date': pre_date, 'actual_date': ''},
    ])

    result = _make_enhancer(disclosure_df=df).enhance('600519.SH')

    metrics = {m.key: m.value for m in result.key_metrics}
    assert metrics['days_to_disclosure'] == 7
    assert '距财报披露约 7 天' in result.summary

    rows = result.details.tables[0].rows
    assert any(r['type'] == '财报披露' and '中报' in r['title'] for r in rows)


def test_disclosure_beyond_window_sets_metric_but_no_event():
    today = datetime.now()
    pre_date = (today + timedelta(days=DISCLOSURE_ALERT_DAYS + 20)).strftime('%Y%m%d')
    df = pd.DataFrame([
        {'ts_code': '600519.SH', 'ann_date': '', 'end_date': '20261231',
         'pre_date': pre_date, 'actual_date': ''},
    ])

    result = _make_enhancer(disclosure_df=df).enhance('600519.SH')

    metrics = {m.key: m.value for m in result.key_metrics}
    assert metrics['days_to_disclosure'] == DISCLOSURE_ALERT_DAYS + 20
    assert '距财报披露' not in result.summary
    assert not result.details.tables  # 无事件行


def test_recent_actual_disclosure_appears_as_event():
    today = datetime.now()
    actual_date = (today - timedelta(days=5)).strftime('%Y%m%d')
    df = pd.DataFrame([
        {'ts_code': '600519.SH', 'ann_date': '', 'end_date': '20260331',
         'pre_date': actual_date, 'actual_date': actual_date},
    ])

    result = _make_enhancer(disclosure_df=df).enhance('600519.SH')

    rows = result.details.tables[0].rows
    assert any(r['type'] == '财报披露' and '已披露' in r['title'] for r in rows)


def test_no_disclosure_data_keeps_module_working():
    result = _make_enhancer(disclosure_df=None).enhance('600519.SH')
    assert result.available
    metrics = {m.key: m.value for m in result.key_metrics}
    assert metrics['days_to_disclosure'] is None
    assert '近30日无重大公司事件' in result.summary


def test_report_period_label():
    assert EventsEnhancer._report_period_label('20260630') == '2026年中报'
    assert EventsEnhancer._report_period_label('20261231') == '2026年年报'
    assert EventsEnhancer._report_period_label('20260331') == '2026年一季报'
    assert EventsEnhancer._report_period_label('20260930') == '2026年三季报'
    assert EventsEnhancer._report_period_label('bad') == '定期报告'
