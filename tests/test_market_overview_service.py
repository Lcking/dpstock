import pandas as pd

from services.market_overview_service import MarketIndexSpec, MarketOverviewService


def test_a_share_index_prefers_tushare_daily_and_sorts_descending_rows(monkeypatch):
    service = MarketOverviewService()

    tushare_rows = pd.DataFrame(
        [
            {"trade_date": "20260318", "close": 4038.87},
            {"trade_date": "20260317", "close": 4049.91},
            {"trade_date": "20260314", "close": 4084.79},
        ]
    )

    class _FakeTushareClient:
        is_available = True

        @staticmethod
        def ensure_initialized(log_missing_token: bool = False):
            return None

        @staticmethod
        def get_index_daily(ts_code: str, start_date: str = None, end_date: str = None):
            assert ts_code == "000001.SH"
            return tushare_rows

    monkeypatch.setattr("services.market_overview_service.tushare_client", _FakeTushareClient())

    item = service._fetch_index(
        MarketIndexSpec(
            key="shanghai",
            name="上证指数",
            market="A",
            symbol="000001.SH",
            tushare_symbol="000001.SH",
        )
    )

    assert item["status"] == "ok"
    assert item["price"] == 4038.87
    assert item["change"] == -11.04
    assert item["change_percent"] == -0.27
    assert item["trend"] == [4084.79, 4049.91, 4038.87]
