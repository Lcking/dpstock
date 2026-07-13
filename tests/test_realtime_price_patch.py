"""A 股日线收盘后用新浪实时价校正最后一根。"""
import pandas as pd

from services.data_provenance import build_data_provenance
from services.stock_data_provider import StockDataProvider


def _hist_df_stale_today() -> pd.DataFrame:
    """模拟日线已有今日但收盘价仍是不完整的 10.72（文章 1706 现场）。"""
    dates = pd.to_datetime(["2026-07-08", "2026-07-09", "2026-07-10"])
    return pd.DataFrame(
        {
            "Open": [11.28, 10.80, 11.03],
            "Close": [10.69, 11.03, 10.72],  # 今日错误/未结算
            "High": [11.42, 11.10, 11.20],
            "Low": [10.42, 10.60, 10.70],
            "Volume": [3.4e8, 3.3e8, 3.0e8],
            "Amount": [3.6e9, 3.5e9, 3.2e9],
            "Change": [-0.33, 0.34, -0.31],
            "Change_pct": [-2.99, 3.18, -2.81],
        },
        index=dates,
    )


def _hist_df_missing_today() -> pd.DataFrame:
    dates = pd.to_datetime(["2026-07-08", "2026-07-09"])
    return pd.DataFrame(
        {
            "Open": [11.28, 10.80],
            "Close": [10.69, 11.03],
            "High": [11.42, 11.10],
            "Low": [10.42, 10.60],
            "Volume": [3.4e8, 3.3e8],
            "Amount": [3.6e9, 3.5e9],
            "Change": [-0.33, 0.34],
            "Change_pct": [-2.99, 3.18],
        },
        index=dates,
    )


def _sina_quote_002129() -> dict:
    return {
        "open": 11.03,
        "prev_close": 11.03,
        "price": 10.66,
        "high": 11.39,
        "low": 10.65,
        "volume": 343544008.0,
        "amount": 3801721943.63,
        "trade_date": "2026-07-10",
        "trade_time": "15:18:45",
        "name": "TCL中环",
    }


def test_to_sina_symbol():
    assert StockDataProvider._to_sina_a_share_symbol("002129") == "sz002129"
    assert StockDataProvider._to_sina_a_share_symbol("600519") == "sh600519"


def test_patch_updates_incomplete_today_close():
    """复现 analysis/1706：日线今日 10.72，实时收盘 10.66，应覆盖。"""
    provider = StockDataProvider()
    df = _hist_df_stale_today()
    patched = provider.patch_a_share_latest_bar_with_realtime(
        df, "002129", quote=_sina_quote_002129()
    )
    assert float(patched.iloc[-1]["Close"]) == 10.66
    assert patched.index[-1].strftime("%Y-%m-%d") == "2026-07-10"
    assert patched.attrs.get("realtime_patched") is True
    assert "15:18" in patched.attrs.get("realtime_as_of", "")


def test_patch_appends_when_daily_missing_today():
    provider = StockDataProvider()
    df = _hist_df_missing_today()
    patched = provider.patch_a_share_latest_bar_with_realtime(
        df, "002129", quote=_sina_quote_002129()
    )
    assert len(patched) == len(df) + 1
    assert patched.index[-1].strftime("%Y-%m-%d") == "2026-07-10"
    assert float(patched.iloc[-1]["Close"]) == 10.66
    assert float(patched.iloc[-2]["Close"]) == 11.03


def test_parse_sina_realtime_text(monkeypatch):
    from services import realtime_quote

    realtime_quote.clear_quote_cache()
    provider = StockDataProvider()
    payload = (
        'var hq_str_sz002129="TCL中环,11.030,11.030,10.660,11.390,10.650,'
        '10.660,10.670,343544008,3801721943.630,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,'
        '2026-07-10,15:18:45,00";'
    )

    class _Resp:
        text = payload
        def raise_for_status(self):
            return None

    class _Client:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get(self, *a, **k):
            return _Resp()

    import httpx
    monkeypatch.setattr(httpx, "Client", _Client)
    quote = provider.fetch_a_share_sina_realtime("002129")
    realtime_quote.clear_quote_cache()
    assert quote is not None
    assert quote["price"] == 10.66
    assert quote["trade_date"] == "2026-07-10"
    assert quote["prev_close"] == 11.03


def test_provenance_reflects_realtime_patch():
    provider = StockDataProvider()
    df = provider.patch_a_share_latest_bar_with_realtime(
        _hist_df_stale_today(), "002129", quote=_sina_quote_002129()
    )
    provenance = build_data_provenance("A", df)
    assert provenance["data_source"] == "日线 + 新浪实时补丁"
    assert "2026-07-10" in provenance["data_as_of"]
    assert "实时" in provenance["data_provenance_label"]
