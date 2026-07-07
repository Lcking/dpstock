import asyncio

import pandas as pd
import pytest

from services.stock_analyzer_service import StockAnalyzerService
from services.stock_data_provider import StockDataProvider


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("159941", 0),
        ("159941.SZ", 0),
        ("510300", 1),
        ("561550", 1),
        ("161725", 0),
    ],
)
def test_infer_eastmoney_market_id(code, expected):
    provider = StockDataProvider()
    assert provider._infer_eastmoney_market_id(code) == expected


def test_fetch_fund_hist_eastmoney_returns_normalized_columns():
    provider = StockDataProvider()
    df = provider._fetch_fund_hist_eastmoney(
        "159941",
        start_date="20250601",
        end_date="20250706",
        adjust="qfq",
    )
    if df.empty:
        pytest.skip("eastmoney kline API unreachable (network/proxy)")
    assert list(df.columns) == [
        "日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额",
        "振幅", "涨跌幅", "涨跌额", "换手率",
    ]


@pytest.mark.asyncio
async def test_etf_kline_accepts_exchange_suffix_codes():
    service = StockAnalyzerService()
    data = await service.get_kline_data("159915.SZ", "ETF", days=20)
    assert "error" not in data
    assert len(data["dates"]) > 0
    assert len(data["values"]) == len(data["dates"])


@pytest.mark.asyncio
async def test_etf_kline_works_for_qdii_159941():
    service = StockAnalyzerService()
    data = await service.get_kline_data("159941", "ETF", days=20)
    assert "error" not in data
    assert len(data["dates"]) > 0
    assert len(data["values"]) == len(data["dates"])


def test_etf_fetch_falls_back_when_akshare_returns_empty(monkeypatch):
    provider = StockDataProvider()
    sample = pd.DataFrame({
        "日期": ["2025-06-03"],
        "开盘": [1.18],
        "收盘": [1.176],
        "最高": [1.181],
        "最低": [1.175],
        "成交量": [4798316],
        "成交额": [565090384.5],
        "振幅": [0.51],
        "涨跌幅": [0.34],
        "涨跌额": [0.004],
        "换手率": [2.13],
    })

    monkeypatch.setattr(provider, "_fetch_fund_hist_eastmoney", lambda *args, **kwargs: pd.DataFrame())
    monkeypatch.setattr(provider, "_fetch_fund_hist_yfinance", lambda *args, **kwargs: sample)

    import akshare as ak

    def _empty_akshare(**kwargs):
        return pd.DataFrame()

    monkeypatch.setattr(ak, "fund_etf_hist_em", _empty_akshare)

    df = asyncio.run(
        provider.get_stock_data("159941", "ETF", start_date="20250601", end_date="20250706")
    )
    assert not df.empty
    assert len(df) == 1
