from datetime import datetime, timedelta
import json
import sqlite3
import uuid
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from database.db_factory import DatabaseFactory
from services.journal.service import JournalService
from services.journal.evaluator import evaluate_journal_conditions


def _price_frame(rows):
    start = datetime(2026, 5, 1)
    data = []
    for idx, row in enumerate(rows):
        data.append(
            {
                "Date": start + timedelta(days=idx),
                "Open": row.get("open", row["close"]),
                "High": row.get("high", row["close"]),
                "Low": row.get("low", row["close"]),
                "Close": row["close"],
                "Volume": row["volume"],
            }
        )
    return pd.DataFrame(data).set_index("Date")


def _base_candidate_descriptions():
    return {
        "A": "价格突破10.13（近30日最高价）且成交量连续2日高于20日均量1.5倍。",
        "B": "价格在9.0-9.5区间震荡超过3个交易日，成交量回落至20日均量的0.8-1.2倍。",
        "C": "价格跌破7.64（MA20）且成交量放大至20日均量的1.3倍以上。",
    }


def test_bullish_breakout_is_supported_when_price_and_volume_trigger():
    rows = [{"close": 9.7, "volume": 1000} for _ in range(20)]
    rows.extend(
        [
            {"close": 10.2, "high": 10.22, "volume": 1700},
            {"close": 10.35, "high": 10.4, "volume": 1800},
        ]
    )

    result = evaluate_journal_conditions(
        selected_candidate="A",
        candidate_descriptions=_base_candidate_descriptions(),
        price_data=_price_frame(rows),
    )

    assert result["outcome"] == "supported"
    assert result["actual_path"] == "A"
    assert result["selected_condition"]["status"] == "triggered"
    assert result["selected_condition"]["price"]["threshold"] == 10.13
    assert result["selected_condition"]["volume"]["required_consecutive_days"] == 2
    assert "看涨条件已触发" in result["summary"]


def test_bullish_breakout_is_uncertain_when_price_triggers_but_volume_does_not():
    rows = [{"close": 9.7, "volume": 1000} for _ in range(20)]
    rows.extend(
        [
            {"close": 10.18, "high": 10.22, "volume": 1050},
            {"close": 10.2, "high": 10.25, "volume": 1100},
        ]
    )

    result = evaluate_journal_conditions(
        selected_candidate="A",
        candidate_descriptions=_base_candidate_descriptions(),
        price_data=_price_frame(rows),
    )

    assert result["outcome"] == "uncertain"
    assert result["actual_path"] is None
    assert result["selected_condition"]["status"] == "partially_triggered"
    assert "价格已突破" in result["summary"]
    assert "量能未确认" in result["summary"]


def test_bullish_judgment_is_falsified_when_reverse_candidate_triggers():
    rows = [{"close": 9.2, "volume": 1000} for _ in range(20)]
    rows.append({"close": 7.55, "low": 7.5, "volume": 1500})

    result = evaluate_journal_conditions(
        selected_candidate="A",
        candidate_descriptions=_base_candidate_descriptions(),
        price_data=_price_frame(rows),
    )

    assert result["outcome"] == "falsified"
    assert result["actual_path"] == "C"
    assert result["selected_condition"]["status"] == "not_triggered"
    assert result["candidate_results"]["C"]["status"] == "triggered"
    assert "市场走出了 C" in result["summary"]


def test_review_record_persists_system_evaluation_from_saved_candidate_conditions():
    db_path = Path("data") / f"test_journal_eval_{uuid.uuid4().hex}.db"
    db_path.parent.mkdir(exist_ok=True)
    user_id = "user_eval"
    record_id = "jr_eval_1"

    try:
        DatabaseFactory.initialize(str(db_path))
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
                    user_id,
                    "600726",
                    "A",
                    "[]",
                    "[]",
                    json.dumps(
                        {
                            "snapshot_time": "2026-05-01T00:00:00Z",
                            "candidates": [
                                {"option_id": key, "description": value}
                                for key, value in _base_candidate_descriptions().items()
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    "{}",
                    "2026-05-29T00:00:00Z",
                    "due",
                    "2026-05-01T00:00:00Z",
                    "2026-05-29T00:00:00Z",
                ),
            )
            conn.commit()

        rows = [{"close": 9.7, "volume": 1000} for _ in range(20)]
        rows.extend(
            [
                {"close": 10.2, "high": 10.22, "volume": 1700},
                {"close": 10.35, "high": 10.4, "volume": 1800},
            ]
        )

        with patch(
            "services.stock_data_provider.StockDataProvider._get_stock_data_sync",
            return_value=_price_frame(rows),
        ):
            result = JournalService().review_record(record_id, user_id, notes="复盘补充")

        assert result["review"]["outcome"] == "supported"
        assert result["review"]["system_evaluation"]["actual_path"] == "A"
        assert "看涨条件已触发" in result["review"]["system_evaluation"]["summary"]
    finally:
        if db_path.exists():
            db_path.unlink()


def test_evaluate_record_returns_system_evaluation_without_marking_reviewed():
    db_path = Path("data") / f"test_journal_preview_{uuid.uuid4().hex}.db"
    db_path.parent.mkdir(exist_ok=True)
    user_id = "user_preview"
    record_id = "jr_preview_1"

    try:
        DatabaseFactory.initialize(str(db_path))
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
                    user_id,
                    "600726",
                    "A",
                    "[]",
                    "[]",
                    json.dumps(
                        {
                            "snapshot_time": "2026-05-01T00:00:00Z",
                            "candidates": [
                                {"option_id": key, "description": value}
                                for key, value in _base_candidate_descriptions().items()
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    "{}",
                    "2026-05-29T00:00:00Z",
                    "due",
                    "2026-05-01T00:00:00Z",
                    "2026-05-29T00:00:00Z",
                ),
            )
            conn.commit()

        rows = [{"close": 9.7, "volume": 1000} for _ in range(20)]
        rows.extend(
            [
                {"close": 10.2, "high": 10.22, "volume": 1700},
                {"close": 10.35, "high": 10.4, "volume": 1800},
            ]
        )

        with patch(
            "services.stock_data_provider.StockDataProvider._get_stock_data_sync",
            return_value=_price_frame(rows),
        ):
            result = JournalService().evaluate_record(record_id, user_id)

        assert result["outcome"] == "supported"
        assert result["actual_path"] == "A"

        with sqlite3.connect(db_path) as conn:
            status, review = conn.execute(
                "SELECT status, review FROM judgments WHERE id = ?", (record_id,)
            ).fetchone()
        assert status == "due"
        assert review is None
    finally:
        if db_path.exists():
            db_path.unlink()
