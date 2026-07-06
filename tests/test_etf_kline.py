import asyncio

import pytest

from services.stock_analyzer_service import StockAnalyzerService


@pytest.mark.asyncio
async def test_etf_kline_accepts_exchange_suffix_codes():
    service = StockAnalyzerService()
    data = await service.get_kline_data("159915.SZ", "ETF", days=20)
    assert "error" not in data
    assert len(data["dates"]) > 0
    assert len(data["values"]) == len(data["dates"])
