import uuid
from datetime import datetime
from pathlib import Path

import sqlite3

from database.db_factory import DatabaseFactory
from scripts.run_migrations import run_migrations
from services.risk_stock_service import RiskStockService
from services.watchlist_risk_alert_service import WatchlistRiskAlertService


def _setup_db(db_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DB_PATH", str(db_path))
    run_migrations()
    DatabaseFactory.initialize(str(db_path))


def _seed_watchlist(db_path: Path, user_id: str, ts_code: str, name: str) -> None:
    now = datetime.utcnow().isoformat() + "Z"
    watchlist_id = f"wl_{uuid.uuid4().hex[:8]}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO watchlists (id, user_id, name, created_at, updated_at)
            VALUES (?, ?, '默认自选', ?, ?)
            """,
            (watchlist_id, user_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO watchlist_items (watchlist_id, ts_code, name, added_at)
            VALUES (?, ?, ?, ?)
            """,
            (watchlist_id, ts_code, name, now),
        )
        conn.commit()


def test_sync_alerts_creates_unread_items_for_watchlist_matches(tmp_path, monkeypatch):
    db_path = tmp_path / "watchlist_risk_alerts.db"
    _setup_db(db_path, monkeypatch)

    RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [
            {"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0},
            {"ts_code": "002001.SZ", "name": "三连板示例", "limit_up_days": 3},
        ],
        source="test",
    )
    _seed_watchlist(db_path, "user_a", "600001.SH", "ST示例")
    _seed_watchlist(db_path, "user_b", "300001.SZ", "普通股")

    service = WatchlistRiskAlertService(db_path=str(db_path))
    result = service.sync_alerts_for_trade_date("20260618")

    assert result["created"] == 1
    assert result["matched_users"] == 1
    assert service.get_unread_count("user_a") == 1
    assert service.get_unread_count("user_b") == 0

    alerts = service.list_alerts("user_a")
    assert alerts["unread_count"] == 1
    assert alerts["items"][0]["ts_code"] == "600001.SH"
    assert "ST股" in alerts["items"][0]["tags"]


def test_sync_alerts_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "watchlist_risk_alerts_idempotent.db"
    _setup_db(db_path, monkeypatch)

    RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="test",
    )
    _seed_watchlist(db_path, "user_a", "600001.SH", "ST示例")

    service = WatchlistRiskAlertService(db_path=str(db_path))
    first = service.sync_alerts_for_trade_date("20260618")
    second = service.sync_alerts_for_trade_date("20260618")

    assert first["created"] == 1
    assert second["created"] == 0
    assert service.get_unread_count("user_a") == 1


def test_mark_all_read_clears_unread_count(tmp_path, monkeypatch):
    db_path = tmp_path / "watchlist_risk_alerts_read.db"
    _setup_db(db_path, monkeypatch)

    RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="test",
    )
    _seed_watchlist(db_path, "user_a", "600001.SH", "ST示例")

    service = WatchlistRiskAlertService(db_path=str(db_path))
    service.sync_alerts_for_trade_date("20260618")
    assert service.get_unread_count("user_a") == 1

    updated = service.mark_all_read("user_a")
    assert updated["updated"] == 1
    assert service.get_unread_count("user_a") == 0


def test_risk_alert_routes_return_unread_count_and_list(tmp_path, monkeypatch):
    db_path = tmp_path / "watchlist_risk_alert_routes.db"
    _setup_db(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="test",
    )
    _seed_watchlist(db_path, "cookie_test_user", "600001.SH", "ST示例")
    WatchlistRiskAlertService(db_path=str(db_path)).sync_alerts_for_trade_date("20260618")

    from fastapi.testclient import TestClient
    from web_server import app

    # Importing web_server resets DatabaseFactory via QuotaService() defaults.
    DatabaseFactory.initialize(str(db_path))

    with TestClient(app) as client:
        count_response = client.get("/api/watchlists/risk-alerts/unread-count")
        list_response = client.get("/api/watchlists/risk-alerts", params={"unread_only": True})

    assert count_response.status_code == 200
    assert list_response.status_code == 200
    assert "count" in count_response.json()
    assert "items" in list_response.json()
