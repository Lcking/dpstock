import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from database.db_factory import DatabaseFactory
from services.judgment_accuracy_service import JudgmentAccuracyService


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


def test_public_accuracy_stats_aggregates_reviewed_outcomes(tmp_path):
    db_path = tmp_path / "accuracy_stats.db"
    DatabaseFactory.initialize(str(db_path))
    _create_judgments_table(db_path)

    created_at = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    rows = [
        ("jr1", "supported"),
        ("jr2", "supported"),
        ("jr3", "falsified"),
    ]
    with sqlite3.connect(db_path) as conn:
        for record_id, outcome in rows:
            conn.execute(
                """
                INSERT INTO judgments (
                    id, user_id, stock_code, candidate, selected_premises,
                    selected_risk_checks, constraints, snapshot, validation_date,
                    status, review, created_at, updated_at
                ) VALUES (?, 'u1', '600519', 'A', '[]', '[]', '{}', '{}', ?, 'reviewed', ?, ?, ?)
                """,
                (
                    record_id,
                    created_at,
                    json.dumps({"outcome": outcome}, ensure_ascii=False),
                    created_at,
                    created_at,
                ),
            )
        conn.commit()

    stats = JudgmentAccuracyService().get_public_accuracy_stats(window_days=90)

    assert stats["reviewed_count"] == 3
    assert stats["support_rate"] == 66.67
    assert stats["outcome_counts"]["supported"] == 2
    assert "仅供参考" in stats["disclaimer"]
