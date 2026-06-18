import json
import sqlite3
from pathlib import Path

from database.db_factory import DatabaseFactory
from scripts.run_migrations import run_migrations
from services.risk_stock_service import RiskStockService


def _run_all_migrations(db_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DB_PATH", str(db_path))
    run_migrations()


def test_risk_stock_service_classifies_st_and_three_limit_up(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_stocks.db"
    _run_all_migrations(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    service = RiskStockService(db_path=str(db_path))
    source_rows = [
        {
            "ts_code": "600001.SH",
            "name": "ST示例",
            "market": "主板",
            "limit_up_days": 0,
        },
        {
            "ts_code": "002001.SZ",
            "name": "三连板示例",
            "market": "主板",
            "limit_up_days": 3,
        },
        {
            "ts_code": "300001.SZ",
            "name": "普通股票",
            "market": "创业板",
            "limit_up_days": 1,
        },
    ]

    refreshed = service.refresh_from_rows("20260618", source_rows, source="unit-test")

    assert refreshed["count"] == 2
    items = service.get_items(trade_date="20260618")
    assert len(items) == 2

    by_code = {item["ts_code"]: item for item in items}
    st_item = by_code["600001.SH"]
    assert st_item["is_st"] == 1
    assert st_item["risk_level"] == "high"
    assert "ST股" in json.loads(st_item["tags_json"])

    board_item = by_code["002001.SZ"]
    assert board_item["limit_up_days"] == 3
    assert "三连板" in json.loads(board_item["tags_json"])
    assert "高度板" in json.loads(board_item["tags_json"])


def test_risk_stock_refresh_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_stocks_idempotent.db"
    _run_all_migrations(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    service = RiskStockService(db_path=str(db_path))
    row = {
        "ts_code": "600001.SH",
        "name": "ST示例",
        "market": "主板",
        "limit_up_days": 4,
    }

    service.refresh_from_rows("20260618", [row], source="unit-test")
    service.refresh_from_rows("20260618", [row], source="unit-test")

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM risk_stock_items").fetchone()[0]

    assert count == 1
    item = service.get_items(trade_date="20260618")[0]
    assert "四连板+" in json.loads(item["tags_json"])
