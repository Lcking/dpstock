"""
Daily LLM / analyze usage rollup for ops dashboard (N7).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from database.db_factory import DatabaseFactory
from database.sqlite_utils import run_with_busy_retry
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
            def _write() -> None:
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

            run_with_busy_retry(_write)
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

    def _analysis_records_table_exists(self, cursor) -> bool:
        row = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_records'"
        ).fetchone()
        return bool(row)

    def rollup_from_analysis_records(self, *, days: int = 7) -> List[Dict[str, Any]]:
        """Historical analyze usage from quota records (available before llm_usage_daily)."""
        days = max(1, min(int(days), 90))
        start_date = (date.today() - timedelta(days=days - 1)).isoformat()
        try:
            with DatabaseFactory.get_connection() as conn:
                cursor = conn.cursor()
                if not self._analysis_records_table_exists(cursor):
                    return []
                rows = cursor.execute(
                    """
                    WITH sessions AS (
                        SELECT
                            ar.analysis_date AS usage_date,
                            ar.user_id,
                            COUNT(*) AS stock_count,
                            CASE
                                WHEN u.email_verified = 1
                                  OR (u.primary_email IS NOT NULL AND TRIM(u.primary_email) != '')
                                THEN ?
                                ELSE ?
                            END AS user_type
                        FROM analysis_records ar
                        LEFT JOIN users u ON u.user_id = ar.user_id
                        WHERE ar.analysis_date >= ?
                        GROUP BY ar.analysis_date, ar.user_id, user_type
                    )
                    SELECT
                        usage_date,
                        user_type,
                        COUNT(*) AS call_count,
                        SUM(stock_count) AS stock_count
                    FROM sessions
                    GROUP BY usage_date, user_type
                    ORDER BY usage_date DESC, user_type ASC
                    """,
                    (
                        USER_TYPE_AUTHENTICATED,
                        USER_TYPE_ANONYMOUS,
                        start_date,
                    ),
                ).fetchall()
            return [dict(row) for row in rows or []]
        except Exception as exc:
            logger.warning(f"[LlmUsage] rollup_from_analysis_records skipped: {exc}")
            return []

    def get_summary(self, *, days: int = 7) -> Dict[str, Any]:
        days = max(1, min(int(days), 90))
        tracked_rows = self.get_daily_usage(days=days)
        historical_rows = self.rollup_from_analysis_records(days=days)

        # Prefer historical rollup for dashboard; overlay today's tracked counters when present.
        daily_by_key = {
            (row.get("usage_date"), row.get("user_type")): dict(row)
            for row in historical_rows
        }
        for row in tracked_rows:
            key = (row.get("usage_date"), row.get("user_type"))
            if key in daily_by_key and row.get("usage_date") == date.today().isoformat():
                daily_by_key[key] = dict(row)
            elif key not in daily_by_key:
                daily_by_key[key] = dict(row)

        rows = sorted(
            daily_by_key.values(),
            key=lambda item: (item.get("usage_date") or "", item.get("user_type") or ""),
            reverse=True,
        )

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

        source = "analysis_records"
        if tracked_rows and not historical_rows:
            source = "llm_usage_daily"
        elif tracked_rows and historical_rows:
            source = "analysis_records+llm_usage_daily"

        return {
            "days": days,
            "source": source,
            "daily": rows,
            "totals": totals,
            "tracked_today": [row for row in tracked_rows if row.get("usage_date") == date.today().isoformat()],
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    def check_usage_alerts(self) -> Dict[str, Any]:
        import os

        anonymous_stock_threshold = max(
            int(os.getenv("OPS_LLM_ANONYMOUS_STOCK_THRESHOLD", "200")),
            1,
        )
        authenticated_stock_threshold = max(
            int(os.getenv("OPS_LLM_AUTHENTICATED_STOCK_THRESHOLD", "500")),
            1,
        )
        today = date.today().isoformat()
        summary = self.get_summary(days=1)
        anonymous_today = 0
        authenticated_today = 0
        for row in summary.get("daily") or []:
            if row.get("usage_date") != today:
                continue
            if row.get("user_type") == USER_TYPE_ANONYMOUS:
                anonymous_today += int(row.get("stock_count") or 0)
            elif row.get("user_type") == USER_TYPE_AUTHENTICATED:
                authenticated_today += int(row.get("stock_count") or 0)

        alerts = []
        if anonymous_today >= anonymous_stock_threshold:
            alerts.append(
                {
                    "level": "warning",
                    "key": "anonymous_stock_spike",
                    "message": (
                        f"今日匿名分析标的数 {anonymous_today} 已达到阈值 "
                        f"{anonymous_stock_threshold}"
                    ),
                    "value": anonymous_today,
                    "threshold": anonymous_stock_threshold,
                }
            )
        if authenticated_today >= authenticated_stock_threshold:
            alerts.append(
                {
                    "level": "info",
                    "key": "authenticated_stock_spike",
                    "message": (
                        f"今日绑定用户分析标的数 {authenticated_today} 已达到阈值 "
                        f"{authenticated_stock_threshold}"
                    ),
                    "value": authenticated_today,
                    "threshold": authenticated_stock_threshold,
                }
            )
        return {
            "usage_date": today,
            "anonymous_stock_count": anonymous_today,
            "authenticated_stock_count": authenticated_today,
            "thresholds": {
                "anonymous_stock_count": anonymous_stock_threshold,
                "authenticated_stock_count": authenticated_stock_threshold,
            },
            "alerts": alerts,
        }


llm_usage_service = LlmUsageService()
