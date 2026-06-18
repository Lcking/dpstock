from pathlib import Path

from fastapi.testclient import TestClient

from database.db_factory import DatabaseFactory
from scripts.run_migrations import run_migrations
from services.risk_stock_export import build_export_rows, render_csv_bytes, render_xlsx_bytes
from services.risk_stock_service import RiskStockService


def _run_all_migrations(db_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DB_PATH", str(db_path))
    run_migrations()


def test_build_export_rows_localizes_fields():
    rows = build_export_rows(
        [
            {
                "trade_date": "20260618",
                "ts_code": "600001.SH",
                "name": "ST示例",
                "market": "主板",
                "tags": ["ST股"],
                "limit_up_days": 0,
                "risk_level": "high",
                "reason": "股票名称包含 ST 风险标识",
            }
        ]
    )

    assert rows[0]["trade_date"] == "20260618"
    assert rows[0]["ts_code"] == "600001.SH"
    assert rows[0]["tags"] == "ST股"
    assert rows[0]["risk_level"] == "高风险"


def test_render_csv_and_xlsx_bytes():
    items = [
        {
            "trade_date": "20260618",
            "ts_code": "002001.SZ",
            "name": "三连板示例",
            "market": "电子",
            "tags": ["三连板", "高度板"],
            "limit_up_days": 3,
            "risk_level": "high",
            "reason": "连续涨停 3 天",
        }
    ]

    csv_bytes = render_csv_bytes(items)
    xlsx_bytes = render_xlsx_bytes(items)

    assert csv_bytes.startswith(b"\xef\xbb\xbf")
    assert "三连板示例".encode("utf-8") in csv_bytes
    assert xlsx_bytes.startswith(b"PK")


def test_public_risk_stock_list_returns_latest_items(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_stock_routes.db"
    _run_all_migrations(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="test",
    )

    from web_server import app
    DatabaseFactory.initialize(str(db_path))

    with TestClient(app) as client:
        response = client.get("/api/risk-stocks")

    assert response.status_code == 200
    data = response.json()
    assert data["trade_date"] == "20260618"
    assert data["data_status"] == "ready"
    assert data["items"][0]["ts_code"] == "600001.SH"
    assert "ST股" in data["items"][0]["tags"]


def test_public_risk_stock_export_csv_and_xlsx(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_stock_export_routes.db"
    _run_all_migrations(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="test",
    )

    from web_server import app
    DatabaseFactory.initialize(str(db_path))

    with TestClient(app) as client:
        csv_response = client.get("/api/risk-stocks/export/csv")
        xlsx_response = client.get("/api/risk-stocks/export/xlsx")

    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "attachment" in csv_response.headers["content-disposition"]
    assert "ST示例".encode("utf-8") in csv_response.content

    assert xlsx_response.status_code == 200
    assert "spreadsheetml.sheet" in xlsx_response.headers["content-type"]
    assert xlsx_response.content.startswith(b"PK")
