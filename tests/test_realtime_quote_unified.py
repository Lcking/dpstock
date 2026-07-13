"""统一实时报价模块：tushare/StockDataProvider 两个取数咽喉都要走实时补丁。"""
import pandas as pd
import pytest

from services import realtime_quote
from services.realtime_quote import (
    patch_tushare_daily,
    should_patch_range,
    to_sina_symbol,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    realtime_quote.clear_quote_cache()
    yield
    realtime_quote.clear_quote_cache()


def _quote_002129() -> dict:
    return {
        "open": 11.03,
        "prev_close": 11.03,
        "price": 10.66,
        "high": 11.39,
        "low": 10.65,
        "volume": 343544008.0,  # 股
        "amount": 3801721943.63,  # 元
        "trade_date": "2026-07-10",
        "trade_time": "15:18:45",
        "name": "TCL中环",
    }


def _tushare_daily_stale_today() -> pd.DataFrame:
    """tushare daily 格式（倒序），今日 close 仍是未结算的 10.72。"""
    return pd.DataFrame(
        {
            "ts_code": ["002129.SZ"] * 3,
            "trade_date": ["20260710", "20260709", "20260708"],
            "open": [11.03, 10.80, 11.28],
            "high": [11.20, 11.10, 11.42],
            "low": [10.70, 10.60, 10.42],
            "close": [10.72, 11.03, 10.69],
            "pre_close": [11.03, 10.69, 11.02],
            "change": [-0.31, 0.34, -0.33],
            "pct_chg": [-2.81, 3.18, -2.99],
            "vol": [3000000.0, 3327567.11, 3442098.81],  # 手
            "amount": [3200000.0, 3600000.0, 3700000.0],  # 千元
        }
    )


def _tushare_daily_missing_today() -> pd.DataFrame:
    df = _tushare_daily_stale_today()
    return df[df["trade_date"] != "20260710"].reset_index(drop=True)


def test_to_sina_symbol_supports_ts_code_and_bare():
    assert to_sina_symbol("002129") == "sz002129"
    assert to_sina_symbol("002129.SZ") == "sz002129"
    assert to_sina_symbol("600519.SH") == "sh600519"
    assert to_sina_symbol("000300.SH") == "sh000300"  # 指数带后缀走后缀
    assert to_sina_symbol("159915.SZ") == "sz159915"  # ETF
    assert to_sina_symbol("830799.BJ") is None  # 北交所暂不支持
    assert to_sina_symbol("") is None


def test_patch_tushare_daily_updates_stale_close():
    patched = patch_tushare_daily(_tushare_daily_stale_today(), "002129.SZ", quote=_quote_002129())
    row = patched[patched["trade_date"] == "20260710"].iloc[0]
    assert float(row["close"]) == 10.66
    assert float(row["vol"]) == pytest.approx(3435440.08)  # 股→手
    assert float(row["amount"]) == pytest.approx(3801721.94363)  # 元→千元
    assert float(row["pct_chg"]) == pytest.approx(-3.3545, abs=1e-3)


def test_patch_tushare_daily_appends_missing_today():
    patched = patch_tushare_daily(_tushare_daily_missing_today(), "002129.SZ", quote=_quote_002129())
    assert "20260710" in set(patched["trade_date"].astype(str))
    row = patched[patched["trade_date"] == "20260710"].iloc[0]
    assert float(row["close"]) == 10.66
    # 升序排列后今日应是最后一根（消费方都会 sort_values）
    ordered = patched.sort_values("trade_date")
    assert str(ordered.iloc[-1]["trade_date"]) == "20260710"


def test_patch_tushare_daily_skips_when_close_matches():
    df = _tushare_daily_stale_today()
    df.loc[df["trade_date"] == "20260710", "close"] = 10.66
    patched = patch_tushare_daily(df, "002129.SZ", quote=_quote_002129())
    # 不应改动其它字段
    row = patched[patched["trade_date"] == "20260710"].iloc[0]
    assert float(row["vol"]) == 3000000.0


def test_should_patch_range_guards_historical_requests():
    assert should_patch_range(None) is True
    assert should_patch_range("20990101") is True
    assert should_patch_range("20200101") is False  # 历史回看不许补
    assert should_patch_range("2020-01-01") is False


def test_should_patch_range_respects_kill_switch(monkeypatch):
    monkeypatch.setenv("REALTIME_PRICE_PATCH_DISABLED", "1")
    assert should_patch_range(None) is False


def test_get_quote_uses_ttl_cache(monkeypatch):
    calls = []

    def fake_fetch(code):
        calls.append(code)
        return _quote_002129()

    monkeypatch.setattr(realtime_quote, "_fetch_sina_quote", fake_fetch)
    q1 = realtime_quote.get_quote("002129.SZ")
    q2 = realtime_quote.get_quote("002129")  # 同一 symbol，命中缓存
    assert q1 == q2
    assert len(calls) == 1


def test_tushare_get_daily_applies_realtime_patch(monkeypatch):
    """观察列表价格走的 tushare_client.get_daily 必须吐出实时校正后的价。"""
    from services.tushare.client import tushare_client, TushareClient

    stale = _tushare_daily_stale_today()
    monkeypatch.setattr(TushareClient, "query", lambda self, api, **kw: stale.copy())
    monkeypatch.setattr(realtime_quote, "_fetch_sina_quote", lambda code: _quote_002129())

    df = tushare_client.get_daily("002129.SZ", start_date="20260701", end_date=None)
    row = df[df["trade_date"] == "20260710"].iloc[0]
    assert float(row["close"]) == 10.66


def test_tushare_get_daily_historical_range_untouched(monkeypatch):
    """判卷等历史区间请求绝不能被实时价污染。"""
    from services.tushare.client import tushare_client, TushareClient

    hist = _tushare_daily_missing_today()
    monkeypatch.setattr(TushareClient, "query", lambda self, api, **kw: hist.copy())
    monkeypatch.setattr(
        realtime_quote, "_fetch_sina_quote",
        lambda code: pytest.fail("historical range must not fetch realtime"),
    )

    df = tushare_client.get_daily("002129.SZ", start_date="20260601", end_date="20260709")
    assert "20260710" not in set(df["trade_date"].astype(str))


def test_watchlist_price_info_reflects_patched_close(monkeypatch):
    """端到端：/watchlist 价格 = _get_price_info = 实时校正后的收盘价。"""
    from services.tushare.client import TushareClient
    from services.watchlist.service import WatchlistService

    stale = _tushare_daily_stale_today()
    monkeypatch.setattr(TushareClient, "query", lambda self, api, **kw: stale.copy())
    monkeypatch.setattr(realtime_quote, "_fetch_sina_quote", lambda code: _quote_002129())

    service = WatchlistService.__new__(WatchlistService)  # 跳过 DB 初始化
    price, change_pct, _name = service._get_price_info("002129.SZ", "2026-07-10")
    assert price == 10.66
    assert change_pct == pytest.approx(-0.033545, abs=1e-4)
