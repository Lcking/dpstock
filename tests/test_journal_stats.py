import json
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


def _insert_judgment(
    db_path: Path,
    *,
    record_id: str,
    user_id: str,
    candidate: str,
    status: str,
    review: dict | None = None,
    days_ago: int = 0,
) -> None:
    created_at = datetime.utcnow() - timedelta(days=days_ago)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO judgments (
                id, user_id, stock_code, candidate, selected_premises,
                selected_risk_checks, constraints, snapshot, validation_date,
                status, review, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                user_id,
                "600726",
                candidate,
                "[]",
                "[]",
                "{}",
                "{}",
                (created_at + timedelta(days=3)).isoformat() + "Z",
                status,
                json.dumps(review, ensure_ascii=False) if review else None,
                created_at.isoformat() + "Z",
                created_at.isoformat() + "Z",
            ),
        )
        conn.commit()


def test_get_review_stats_summarizes_recent_judgment_outcomes():
    db_path = Path("data") / f"test_journal_stats_{uuid.uuid4().hex}.db"
    db_path.parent.mkdir(exist_ok=True)
    user_id = "user_stats"
    try:
        DatabaseFactory.initialize(str(db_path))
        _create_judgments_table(db_path)
        _insert_judgment(
            db_path,
            record_id="jr_supported_a",
            user_id=user_id,
            candidate="A",
            status="reviewed",
            review={
                "outcome": "supported",
                "system_evaluation": {"actual_path": "A", "summary": "A 看涨条件已触发"},
            },
            days_ago=1,
        )
        _insert_judgment(
            db_path,
            record_id="jr_falsified_c",
            user_id=user_id,
            candidate="A",
            status="reviewed",
            review={
                "outcome": "falsified",
                "system_evaluation": {"actual_path": "C", "summary": "市场走出了 C"},
            },
            days_ago=2,
        )
        _insert_judgment(
            db_path,
            record_id="jr_uncertain",
            user_id=user_id,
            candidate="B",
            status="reviewed",
            review={
                "outcome": "uncertain",
                "system_evaluation": {"actual_path": None, "summary": "条件未触发"},
            },
            days_ago=3,
        )
        _insert_judgment(
            db_path,
            record_id="jr_active",
            user_id=user_id,
            candidate="B",
            status="active",
            days_ago=0,
        )
        _insert_judgment(
            db_path,
            record_id="jr_other_user",
            user_id="other_user",
            candidate="A",
            status="reviewed",
            review={"outcome": "supported", "system_evaluation": {"actual_path": "A"}},
            days_ago=0,
        )

        stats = JournalService().get_review_stats(user_id=user_id, limit=30)

        assert stats["sample_size"] == 4
        assert stats["reviewed_count"] == 3
        assert stats["pending_count"] == 1
        assert stats["outcome_counts"] == {"supported": 1, "falsified": 1, "uncertain": 1}
        assert stats["support_rate"] == 33.33
        assert stats["actual_path_counts"] == {"A": 1, "C": 1}
        assert stats["most_common_actual_path"] in ("A", "C")
    finally:
        if db_path.exists():
            db_path.unlink()


def test_get_review_stats_handles_empty_user():
    db_path = Path("data") / f"test_journal_stats_empty_{uuid.uuid4().hex}.db"
    db_path.parent.mkdir(exist_ok=True)
    try:
        DatabaseFactory.initialize(str(db_path))
        _create_judgments_table(db_path)

        stats = JournalService().get_review_stats(user_id="empty_user", limit=30)

        assert stats["sample_size"] == 0
        assert stats["reviewed_count"] == 0
        assert stats["support_rate"] is None
        assert stats["most_common_actual_path"] is None
    finally:
        if db_path.exists():
            db_path.unlink()
