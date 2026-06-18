from pathlib import Path

from fastapi.testclient import TestClient

from database.db_factory import DatabaseFactory
from scripts.run_migrations import run_migrations
from services.risk_stock_service import RiskStockService


def _run_all_migrations(db_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DB_PATH", str(db_path))
    run_migrations()


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
