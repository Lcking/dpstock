import uuid
from datetime import datetime
from pathlib import Path

import sqlite3

from database.db_factory import DatabaseFactory
from scripts.run_migrations import run_migrations
from services.notify_pref_service import NotifyPrefService
from services.risk_alert_email_service import (
    create_risk_alert_unsubscribe_token,
    verify_risk_alert_unsubscribe_token,
)
from services.risk_stock_service import RiskStockService
from services.user_service import UserService
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


def _seed_verified_user(db_path: Path, email: str) -> str:
    return UserService(db_path=str(db_path)).create_user(
        primary_email=email,
        email_verified=True,
    )


def _install_fake_sender(monkeypatch, bucket):
    def _fake_send(email, trade_date, alerts, **kwargs):
        bucket.append({"email": email, "trade_date": trade_date, "count": len(alerts)})
        return True, "ok"

    monkeypatch.setattr(
        "services.risk_alert_email_service.send_risk_alert_digest",
        _fake_send,
    )


def test_refresh_triggers_risk_alert_digest_for_verified_user(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_alert_email_send.db"
    _setup_db(db_path, monkeypatch)

    user_id = _seed_verified_user(db_path, "alice@example.com")
    _seed_watchlist(db_path, user_id, "600001.SH", "ST示例")
    sent = []
    _install_fake_sender(monkeypatch, sent)

    result = RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="test",
    )

    assert result["alerts_created"] == 1
    assert result["emails_sent"] == 1
    assert len(sent) == 1
    assert sent[0]["email"] == "alice@example.com"
    assert sent[0]["count"] == 1


def test_risk_alert_digest_is_not_sent_twice_same_day(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_alert_email_dedup.db"
    _setup_db(db_path, monkeypatch)

    user_id = _seed_verified_user(db_path, "alice@example.com")
    _seed_watchlist(db_path, user_id, "600001.SH", "ST示例")
    sent = []
    _install_fake_sender(monkeypatch, sent)

    RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="test",
    )
    second = WatchlistRiskAlertService(db_path=str(db_path)).sync_alerts_for_trade_date(
        "20260618"
    )

    assert second["emails_sent"] == 0
    assert len(sent) == 1


def test_risk_alert_digest_skips_when_notify_pref_disabled(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_alert_email_pref.db"
    _setup_db(db_path, monkeypatch)

    user_id = _seed_verified_user(db_path, "alice@example.com")
    NotifyPrefService(db_path=str(db_path)).set_risk_alert_email(user_id, False)
    _seed_watchlist(db_path, user_id, "600001.SH", "ST示例")
    sent = []
    _install_fake_sender(monkeypatch, sent)

    result = RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="test",
    )

    assert result["alerts_created"] == 1
    assert result["emails_sent"] == 0
    assert len(sent) == 0


def test_risk_alert_digest_skips_without_verified_email(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_alert_email_no_email.db"
    _setup_db(db_path, monkeypatch)

    user_id = UserService(db_path=str(db_path)).get_or_create_user_by_identity(
        identity_type="anonymous",
        identity_value="anon_no_email",
    )
    _seed_watchlist(db_path, user_id, "600001.SH", "ST示例")
    sent = []
    _install_fake_sender(monkeypatch, sent)

    result = RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="test",
    )

    assert result["alerts_created"] == 1
    assert result["emails_sent"] == 0
    assert len(sent) == 0


def test_unsubscribe_token_disables_future_digests(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_alert_email_unsub.db"
    _setup_db(db_path, monkeypatch)

    user_id = _seed_verified_user(db_path, "alice@example.com")
    token = create_risk_alert_unsubscribe_token(user_id)
    assert verify_risk_alert_unsubscribe_token(token) == user_id

    NotifyPrefService(db_path=str(db_path)).set_risk_alert_email(user_id, False)
    _seed_watchlist(db_path, user_id, "600001.SH", "ST示例")
    sent = []
    _install_fake_sender(monkeypatch, sent)

    result = RiskStockService(db_path=str(db_path)).refresh_from_rows(
        "20260618",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="test",
    )

    assert result["emails_sent"] == 0
    assert len(sent) == 0


def test_unsubscribe_endpoint_disables_email_and_returns_html(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_alert_email_route.db"
    _setup_db(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    user_id = _seed_verified_user(db_path, "alice@example.com")
    token = create_risk_alert_unsubscribe_token(user_id)

    from fastapi.testclient import TestClient
    from web_server import app

    DatabaseFactory.initialize(str(db_path))

    with TestClient(app) as client:
        response = client.get("/api/v1/notifications/unsubscribe", params={"token": token})

    assert response.status_code == 200
    assert "已退订风险提醒邮件" in response.text
    assert NotifyPrefService(db_path=str(db_path)).is_risk_alert_email_enabled(user_id) is False


def test_user_center_notify_pref_patch(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_alert_email_user_center.db"
    _setup_db(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    user_id = _seed_verified_user(db_path, "alice@example.com")

    from fastapi.testclient import TestClient
    from web_server import app

    DatabaseFactory.initialize(str(db_path))

    with TestClient(app) as client:
        response = client.patch(
            "/api/user-center/notify-pref",
            json={"risk_alert_email": False},
            headers={"X-Anonymous-Id": user_id},
        )

    assert response.status_code == 200
    assert response.json()["notify_pref"]["risk_alert_email"] is False
