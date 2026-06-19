"""
Public judgment accuracy statistics for trust / GEO surfaces.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from database.db_factory import DatabaseFactory
from services.journal.condition_quality import (
    build_condition_quality_leaderboard,
    extract_selected_condition_description,
)
from services.journal.failure_reasons import failure_reason_label


class JudgmentAccuracyService:
    def __init__(self):
        self.db = DatabaseFactory()

    def get_public_accuracy_stats(self, window_days: int = 90) -> Dict[str, Any]:
        window_days = min(max(int(window_days or 90), 7), 365)
        outcome_counts = {"supported": 0, "falsified": 0, "uncertain": 0}
        reviewed_items: List[Dict[str, Any]] = []
        market_counts: Dict[str, int] = {}

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT candidate, review, constraints, stock_code, created_at
                FROM judgments
                WHERE status = 'reviewed'
                  AND review IS NOT NULL
                  AND datetime(created_at) >= datetime('now', ?)
                ORDER BY created_at DESC
                LIMIT 500
                """,
                (f"-{window_days} day",),
            )
            rows = cursor.fetchall()

        for row in rows:
            review = self._parse_json(row.get("review"))
            if not review:
                continue
            outcome = review.get("outcome")
            if outcome not in outcome_counts:
                outcome = "uncertain"
            outcome_counts[outcome] += 1

            constraints = self._parse_json(row.get("constraints")) or {}
            candidate = str(row.get("candidate") or "").upper()
            reviewed_items.append(
                {
                    "outcome": outcome,
                    "condition_description": extract_selected_condition_description(
                        constraints,
                        candidate,
                    ),
                }
            )

            market = self._infer_market(row.get("stock_code"))
            market_counts[market] = market_counts.get(market, 0) + 1

        reviewed_count = sum(outcome_counts.values())
        support_rate = None
        falsified_rate = None
        if reviewed_count > 0:
            support_rate = round(outcome_counts["supported"] / reviewed_count * 100, 2)
            falsified_rate = round(outcome_counts["falsified"] / reviewed_count * 100, 2)

        return {
            "window_days": window_days,
            "reviewed_count": reviewed_count,
            "outcome_counts": outcome_counts,
            "support_rate": support_rate,
            "falsified_rate": falsified_rate,
            "condition_quality_leaderboard": build_condition_quality_leaderboard(reviewed_items),
            "market_counts": market_counts,
            "disclaimer": "历史验证统计仅供参考，不构成投资建议，也不代表未来表现。",
        }

    def _infer_market(self, stock_code: Optional[str]) -> str:
        code = str(stock_code or "").upper()
        if code.endswith(".HK") or (code.isdigit() and len(code) == 5):
            return "HK"
        if code.endswith(".US") or (code.isalpha() and len(code) <= 5):
            return "US"
        return "A"

    def _parse_json(self, raw: Any) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                return None
        return None
