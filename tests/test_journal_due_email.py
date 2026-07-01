import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import sqlite3

import pytest

from database.db_factory import DatabaseFactory
from scripts.run_migrations import run_migrations
from services.journal.service import JournalService
from services.journal_due_email_service import (
    JournalDueEmailService,
    create_journal_due_unsubscribe_token,
    verify_journal_due_unsubscribe_token,
)
from services.notify_pref_service import NotifyPrefService
from services.user_service import UserService


def _setup_db(db_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DB_PATH", str(db_path))
    run_migrations()
    DatabaseFactory.initialize(str(db_path))


def _seed_verified_user(db_path: Path, email: str) -> str:
    return UserService(db_path=str(db_path)).create_user(
        primary_email=email,
        email_verified=True,
    )


def _insert_due_record(db_path: Path, user_id: str, stock_code: str = "600519.SH") -> str:
    now = datetime.utcnow()
    record_id = f"jr_{uuid.uuid4().hex[:12]}"
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
                record_id,
                user_id,
                stock_code,
                "A",
                "[]",
                "[]",
                "{}",
                json.dumps(
                    {"watchlist_summary": {"name": "贵州茅台", "ts_code": stock_code}},
                    ensure_ascii=False,
                ),
                (now - timedelta(days=1)).isoformat() + "Z",
                "due",
                None,
                (now - timedelta(days=5)).isoformat() + "Z",
                now.isoformat() + "Z",
            ),
        )
        conn.commit()
    return record_id


def test_journal_due_digest_sends_for_verified_user(tmp_path, monkeypatch):
    db_path = tmp_path / "journal_due_email_send.db"
    _setup_db(db_path, monkeypatch)

    user_id = _seed_verified_user(db_path, "alice@example.com")
    _insert_due_record(db_path, user_id)
    sent = []

    def _fake_send(email, digest_date, due_records, **kwargs):
        sent.append({"email": email, "count": len(due_records)})
        return True, "ok"

    monkeypatch.setattr(
        "services.journal_due_email_service.send_journal_due_digest",
        _fake_send,
    )

    result = JournalDueEmailService(db_path=str(db_path)).send_daily_digests("2026-06-18")

    assert result["sent"] == 1
    assert len(sent) == 1
    assert sent[0]["email"] == "alice@example.com"
    assert sent[0]["count"] == 1


def test_journal_due_digest_is_not_sent_twice_same_day(tmp_path, monkeypatch):
    db_path = tmp_path / "journal_due_email_dedup.db"
    _setup_db(db_path, monkeypatch)

    user_id = _seed_verified_user(db_path, "alice@example.com")
    _insert_due_record(db_path, user_id)
    sent = []

    monkeypatch.setattr(
        "services.journal_due_email_service.send_journal_due_digest",
        lambda *args, **kwargs: sent.append(1) or (True, "ok"),
    )

    service = JournalDueEmailService(db_path=str(db_path))
    first = service.send_daily_digests("2026-06-18")
    second = service.send_daily_digests("2026-06-18")

    assert first["sent"] == 1
    assert second["sent"] == 0
    assert len(sent) == 1


def test_journal_due_digest_skips_when_notify_pref_disabled(tmp_path, monkeypatch):
    db_path = tmp_path / "journal_due_email_pref.db"
    _setup_db(db_path, monkeypatch)

    user_id = _seed_verified_user(db_path, "alice@example.com")
    NotifyPrefService(db_path=str(db_path)).set_journal_due_email(user_id, False)
    _insert_due_record(db_path, user_id)

    monkeypatch.setattr(
        "services.journal_due_email_service.send_journal_due_digest",
        lambda *args, **kwargs: pytest.fail("should not send"),
    )

    result = JournalDueEmailService(db_path=str(db_path)).send_daily_digests("2026-06-18")
    assert result["sent"] == 0
    assert result["skipped"] == 1


def test_run_due_check_triggers_digest_when_records_become_due(tmp_path, monkeypatch):
    db_path = tmp_path / "journal_due_check_email.db"
    _setup_db(db_path, monkeypatch)

    user_id = _seed_verified_user(db_path, "alice@example.com")
    now = datetime.utcnow()
    record_id = f"jr_{uuid.uuid4().hex[:12]}"
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
                record_id,
                user_id,
                "600519.SH",
                "A",
                "[]",
                "[]",
                "{}",
                "{}",
                (now - timedelta(seconds=5)).isoformat() + "Z",
                "active",
                None,
                (now - timedelta(days=3)).isoformat() + "Z",
                now.isoformat() + "Z",
            ),
        )
        conn.commit()

    sent = []
    monkeypatch.setattr(
        "services.journal_due_email_service.send_journal_due_digest",
        lambda *args, **kwargs: sent.append(1) or (True, "ok"),
    )
    monkeypatch.setattr(
        JournalService,
        "_auto_evaluate",
        lambda self, row: ("uncertain", [], {"outcome": "uncertain", "summary": "test"}),
    )

    updated = JournalService().run_due_check()
    assert updated == 1
    assert len(sent) == 1


def test_journal_due_unsubscribe_token_roundtrip():
    token = create_journal_due_unsubscribe_token("user_123")
    assert verify_journal_due_unsubscribe_token(token) == "user_123"
