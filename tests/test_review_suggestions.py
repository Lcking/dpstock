from services.journal.review_suggestions import build_review_suggestions


def test_supported_outcome_suggests_lesson_on_strengths():
    suggestions = build_review_suggestions(
        "A",
        {"outcome": "supported", "actual_path": "A"},
    )

    assert suggestions["suggested_failure_reason"] is None
    assert "沉淀" in suggestions["title"]
    assert len(suggestions["bullets"]) >= 2


def test_falsified_reverse_path_suggests_reverse_path_reason():
    suggestions = build_review_suggestions(
        "A",
        {"outcome": "falsified", "actual_path": "B"},
    )

    assert suggestions["suggested_failure_reason"] == "reverse_path"
    assert "B" in suggestions["bullets"][0]


def test_uncertain_volume_gap_suggests_volume_unconfirmed():
    suggestions = build_review_suggestions(
        "B",
        {
            "outcome": "uncertain",
            "selected_condition": {
                "price": {"triggered": True},
                "volume": {"triggered": False},
            },
        },
    )

    assert suggestions["suggested_failure_reason"] == "volume_unconfirmed"


def test_evaluate_record_includes_review_suggestions(tmp_path, monkeypatch):
    import json
    import sqlite3
    import uuid
    from datetime import datetime, timedelta
    from pathlib import Path

    from database.db_factory import DatabaseFactory
    from services.journal import journal_service

    repo_root = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "review_suggestions_eval.db"

    for migration_name in [
        "004_create_watchlist_tables.sql",
        "006_recreate_judgments_table.sql",
        "008_create_user_tables.sql",
    ]:
        sql = (repo_root / "migrations" / migration_name).read_text(encoding="utf-8")
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(sql)
            conn.commit()
        finally:
            conn.close()

    DatabaseFactory.initialize(str(db_path))
    user_id = "suggestion_user"
    record_id = f"jr_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow()

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
                json.dumps(
                    {
                        "evaluation_preview": {
                            "outcome": "falsified",
                            "actual_path": "B",
                            "summary": "test",
                        }
                    },
                    ensure_ascii=False,
                ),
                "{}",
                (now - timedelta(days=1)).isoformat() + "Z",
                "due",
                None,
                (now - timedelta(days=3)).isoformat() + "Z",
                now.isoformat() + "Z",
            ),
        )
        conn.commit()

    result = journal_service.evaluate_record(record_id, user_id)

    assert result["outcome"] == "falsified"
    assert result["review_suggestions"]["suggested_failure_reason"] == "reverse_path"
    assert result["review_suggestions"]["title"]
