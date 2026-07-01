import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from database.db_factory import DatabaseFactory
from services.journal import journal_service


REPO_ROOT = Path(__file__).resolve().parents[1]


def _apply_migration(db_path: Path, migration_name: str) -> None:
    sql = (REPO_ROOT / "migrations" / migration_name).read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def _setup_journal_db(db_path: Path) -> None:
    for migration_name in [
        "004_create_watchlist_tables.sql",
        "006_recreate_judgments_table.sql",
        "008_create_user_tables.sql",
    ]:
        _apply_migration(db_path, migration_name)


def _insert_reviewed_record(
    db_path: Path,
    user_id: str,
    stock_code: str,
    outcome: str,
) -> None:
    now = datetime.utcnow()
    review = {
        "reviewed_at": now.isoformat() + "Z",
        "outcome": outcome,
        "triggers": [],
    }
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO judgments (
                id, user_id, stock_code, candidate, selected_premises,
                selected_risk_checks, constraints, snapshot,
                validation_date, status, review, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"jr_{uuid.uuid4().hex[:12]}",
                user_id,
                stock_code,
                "B",
                "[]",
                "[]",
                json.dumps(
                    {
                        "snapshot_time": (now - timedelta(days=3)).isoformat() + "Z",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "watchlist_summary": {
                            "name": "贵州茅台",
                            "ts_code": "600519.SH",
                        }
                    },
                    ensure_ascii=False,
                ),
                (now - timedelta(days=1)).isoformat() + "Z",
                "reviewed",
                json.dumps(review, ensure_ascii=False),
                (now - timedelta(days=5)).isoformat() + "Z",
                now.isoformat() + "Z",
            ),
        )
        conn.commit()


def test_get_stock_timeline_matches_legacy_and_canonical_codes(tmp_path):
    db_path = tmp_path / "journal_stock_timeline.db"
    _setup_journal_db(db_path)
    DatabaseFactory.initialize(str(db_path))

    user_id = "timeline_user"
    _insert_reviewed_record(db_path, user_id, "600519", "supported")
    _insert_reviewed_record(db_path, user_id, "600519.SH", "falsified")

    timeline = journal_service.get_stock_timeline(user_id=user_id, ts_code="600519.SH")

    assert timeline["ts_code"] == "600519.SH"
    assert timeline["stock_name"] == "贵州茅台"
    assert timeline["total_count"] == 2
    assert timeline["reviewed_count"] == 2
    assert timeline["support_rate"] == 50.0
    assert len(timeline["records"]) == 2


def test_stock_timeline_api_returns_filtered_history(tmp_path, monkeypatch):
    db_path = tmp_path / "journal_stock_timeline_api.db"
    _setup_journal_db(db_path)
    DatabaseFactory.initialize(str(db_path))

    user_id = "timeline_api_user"
    _insert_reviewed_record(db_path, user_id, "600519.SH", "supported")

    import auth.dependencies as auth_deps
    import web_server
    from services.user_service import UserService

    monkeypatch.setenv("DB_PATH", str(db_path))
    test_user_service = UserService(db_path=str(db_path))
    monkeypatch.setattr(auth_deps, "_user_service", test_user_service)
    monkeypatch.setattr(web_server, "user_service", test_user_service)
    monkeypatch.setattr("scripts.run_migrations.run_migrations", lambda: None)

    with TestClient(web_server.app) as client:
        response = client.get(
            "/api/journal/stock-timeline",
            params={"ts_code": "600519"},
            headers={"X-Anonymous-Id": user_id},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ts_code"] == "600519.SH"
    assert data["total_count"] == 1
    assert data["records"][0]["ts_code"] == "600519.SH"
