import pandas as pd

from services.risk_stock_collector import RiskStockCollector, to_ts_code


class _FakeSnapshot:
    def _load_snapshot(self, market: str):
        assert market == "A"
        return [
            {"symbol": "600001", "name": "ST示例", "market": "A"},
            {"symbol": "000001", "name": "平安银行", "market": "A"},
        ]


def test_to_ts_code():
    assert to_ts_code("600001") == "600001.SH"
    assert to_ts_code("000001") == "000001.SZ"


def test_collector_merges_st_and_three_board_rows(monkeypatch):
    collector = RiskStockCollector(snapshot_service=_FakeSnapshot())

    zt_df = pd.DataFrame(
        [
            {"代码": "002001", "名称": "三连板示例", "连板数": 3, "所属行业": "电子"},
            {"代码": "300001", "名称": "普通涨停", "连板数": 1, "所属行业": "医药"},
        ]
    )

    monkeypatch.setattr(collector, "_fetch_zt_pool", lambda trade_date: zt_df)
    monkeypatch.setattr(collector, "_resolve_trade_date", lambda: "20260618")

    trade_date, rows = collector.collect_rows()

    assert trade_date == "20260618"
    by_code = {row["ts_code"]: row for row in rows}
    assert "600001.SH" in by_code
    assert by_code["600001.SH"]["limit_up_days"] == 0
    assert "002001.SZ" in by_code
    assert by_code["002001.SZ"]["limit_up_days"] == 3
    assert "000001.SZ" not in by_code
    assert "300001.SZ" not in by_code
