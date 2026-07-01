import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from database.db_factory import DatabaseFactory

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = REPO_ROOT / "migrations"


def apply_migrations(db_path: Path, migration_names: list[str]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for migration_name in migration_names:
            sql = (MIGRATIONS_DIR / migration_name).read_text(encoding="utf-8")
            conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def _create_judgments_table(db_path: Path) -> None:
    apply_migrations(db_path, ["006_recreate_judgments_table.sql"])


@pytest.fixture
def notification_client(tmp_path, monkeypatch):
    db_path = tmp_path / "notifications_inbox.db"
    apply_migrations(
        db_path,
        [
            "008_create_user_tables.sql",
            "012_create_watchlist_risk_alerts.sql",
        ],
    )
    _create_judgments_table(db_path)
    DatabaseFactory.initialize(str(db_path))

    with DatabaseFactory.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, primary_email, email_verified, profile_completed,
                               is_public_analysis_enabled, status, created_at, last_active_at)
            VALUES ('u1', 'user@example.com', 1, 1, 0, 'active', '2026-06-01', '2026-06-01')
            """
        )
        created_at = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
        conn.execute(
            """
            INSERT INTO judgments (
                id, user_id, stock_code, candidate, selected_premises,
                selected_risk_checks, constraints, snapshot, validation_date,
                status, review, created_at, updated_at
            ) VALUES ('jr1', 'u1', '600519', 'A', '[]', '[]', '{}', '{}', ?, 'due', NULL, ?, ?)
            """,
            (created_at, created_at, created_at),
        )
        conn.execute(
            """
            INSERT INTO watchlist_risk_alerts (
                id, user_id, ts_code, stock_name, trade_date, tags_json,
                risk_level, reason, created_at, read_at
            ) VALUES (
                'ra1', 'u1', '600519', '贵州茅台', '20260630', '["ST"]',
                'high', '测试风险', '2026-06-30T08:00:00Z', NULL
            )
            """
        )
        conn.commit()

    monkeypatch.setenv("DB_PATH", str(db_path))

    from fastapi.testclient import TestClient
    from auth.dependencies import UserContext, get_current_user
    import web_server

    async def fake_user():
        return UserContext(user_id="u1", identity_type="email_anchor", is_authenticated=True)

    web_server.app.dependency_overrides[get_current_user] = fake_user
    client = TestClient(web_server.app)
    yield client
    web_server.app.dependency_overrides.clear()


def test_notification_inbox_returns_due_and_risk_preview(notification_client):
    response = notification_client.get("/api/v1/notifications/inbox")
    assert response.status_code == 200
    body = response.json()
    assert body["due_count"] == 1
    assert body["risk_alert_count"] == 1
    assert body["due_preview"][0]["ts_code"] == "600519"
    assert body["risk_preview"][0]["stock_code"] == "600519" or body["risk_preview"][0].get("ts_code") == "600519"
