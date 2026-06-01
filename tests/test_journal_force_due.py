import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from database.db_factory import DatabaseFactory
from services.journal.service import JournalService


def _create_judgments_table(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE judgments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                stock_code TEXT NOT NULL,
                candidate TEXT,
                selected_premises TEXT,
                selected_risk_checks TEXT,
                constraints TEXT,
                snapshot TEXT,
                validation_date TEXT,
                status TEXT DEFAULT 'active',
                review TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _insert_judgment(db_path: Path, record_id: str, status: str = "active") -> None:
    now = datetime.utcnow()
    validation_date = (now + timedelta(days=3)).isoformat() + "Z"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO judgments (
                id, user_id, stock_code, candidate, selected_premises,
                selected_risk_checks, constraints, snapshot, validation_date,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                "user_force_due",
                "600726",
                "B",
                "[]",
                "[]",
                "{}",
                "{}",
                validation_date,
                status,
                now.isoformat() + "Z",
                now.isoformat() + "Z",
            ),
        )
        conn.commit()


def test_force_due_record_marks_active_judgment_due():
    db_path = Path("data") / f"test_force_due_{uuid.uuid4().hex}.db"
    db_path.parent.mkdir(exist_ok=True)
    record_id = "jr_force_due"
    try:
        DatabaseFactory.initialize(str(db_path))
        _create_judgments_table(db_path)
        _insert_judgment(db_path, record_id, status="active")

        result = JournalService().force_due_record(record_id)

        assert result["ok"] is True
        assert result["status"] == "due"
        assert result["previous_status"] == "active"

        with sqlite3.connect(db_path) as conn:
            status, validation_date = conn.execute(
                "SELECT status, validation_date FROM judgments WHERE id = ?", (record_id,)
            ).fetchone()
        assert status == "due"
        assert datetime.fromisoformat(validation_date.replace("Z", "+00:00")).replace(tzinfo=None) < datetime.utcnow()
    finally:
        if db_path.exists():
            db_path.unlink()


def test_force_due_record_does_not_reopen_reviewed_judgment():
    db_path = Path("data") / f"test_force_due_reviewed_{uuid.uuid4().hex}.db"
    db_path.parent.mkdir(exist_ok=True)
    record_id = "jr_reviewed"
    try:
        DatabaseFactory.initialize(str(db_path))
        _create_judgments_table(db_path)
        _insert_judgment(db_path, record_id, status="reviewed")

        result = JournalService().force_due_record(record_id)

        assert result["ok"] is False
        assert result["status"] == "reviewed"
        assert "active" in result["reason"]

        with sqlite3.connect(db_path) as conn:
            status = conn.execute("SELECT status FROM judgments WHERE id = ?", (record_id,)).fetchone()[0]
        assert status == "reviewed"
    finally:
        if db_path.exists():
            db_path.unlink()
