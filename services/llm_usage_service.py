"""
Daily LLM / analyze usage rollup for ops dashboard (N7).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from database.db_factory import DatabaseFactory
from utils.logger import get_logger

logger = get_logger()

USER_TYPE_AUTHENTICATED = "authenticated"
USER_TYPE_ANONYMOUS = "anonymous"


class LlmUsageService:
    def _table_exists(self, cursor) -> bool:
        row = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_usage_daily'"
        ).fetchone()
        return bool(row)

    def record_analyze(self, *, is_authenticated: bool, stock_count: int = 1) -> None:
        if stock_count <= 0:
            return
        user_type = USER_TYPE_AUTHENTICATED if is_authenticated else USER_TYPE_ANONYMOUS
        usage_date = date.today().isoformat()
        try:
            with DatabaseFactory.get_connection() as conn:
                cursor = conn.cursor()
                if not self._table_exists(cursor):
                    return
                cursor.execute(
                    """
                    INSERT INTO llm_usage_daily (usage_date, user_type, call_count, stock_count)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(usage_date, user_type) DO UPDATE SET
                        call_count = call_count + 1,
                        stock_count = stock_count + excluded.stock_count
                    """,
                    (usage_date, user_type, stock_count),
                )
                conn.commit()
        except Exception as exc:
            logger.warning(f"[LlmUsage] record_analyze skipped: {exc}")

    def get_daily_usage(self, *, days: int = 7) -> List[Dict[str, Any]]:
        days = max(1, min(int(days), 90))
        start_date = (date.today() - timedelta(days=days - 1)).isoformat()
        try:
            with DatabaseFactory.get_connection() as conn:
                cursor = conn.cursor()
                if not self._table_exists(cursor):
                    return []
                rows = cursor.execute(
                    """
                    SELECT usage_date, user_type, call_count, stock_count
                    FROM llm_usage_daily
                    WHERE usage_date >= ?
                    ORDER BY usage_date DESC, user_type ASC
                    """,
                    (start_date,),
                ).fetchall()
            return [dict(row) for row in rows or []]
        except Exception as exc:
            logger.warning(f"[LlmUsage] get_daily_usage skipped: {exc}")
            return []

    def get_summary(self, *, days: int = 7) -> Dict[str, Any]:
        rows = self.get_daily_usage(days=days)
        totals = {
            USER_TYPE_AUTHENTICATED: {"call_count": 0, "stock_count": 0},
            USER_TYPE_ANONYMOUS: {"call_count": 0, "stock_count": 0},
        }
        for row in rows:
            user_type = row.get("user_type")
            if user_type not in totals:
                continue
            totals[user_type]["call_count"] += int(row.get("call_count") or 0)
            totals[user_type]["stock_count"] += int(row.get("stock_count") or 0)
        return {
            "days": days,
            "daily": rows,
            "totals": totals,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }


llm_usage_service = LlmUsageService()
