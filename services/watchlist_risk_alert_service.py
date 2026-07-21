"""
Watchlist risk alert service.

Creates in-app alerts when a user's watchlist symbol appears in the daily risk stock list.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db_factory import DatabaseFactory
from services.risk_stock_service import RiskStockService
from utils.logger import get_logger

logger = get_logger()


class WatchlistRiskAlertService:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            DatabaseFactory.initialize(db_path)
        self.db = DatabaseFactory
        self.risk_stock_service = RiskStockService(db_path=db_path)

    def sync_alerts_for_trade_date(self, trade_date: Optional[str] = None) -> Dict[str, Any]:
        effective_date = trade_date or self.risk_stock_service.get_latest_trade_date()
        if not effective_date:
            return {
                "trade_date": None,
                "created": 0,
                "matched_users": 0,
                "emails_sent": 0,
                "emails_skipped": 0,
                "emails_failed": 0,
            }

        risk_items = self.risk_stock_service.get_items(trade_date=effective_date)
        if not risk_items:
            return {
                "trade_date": effective_date,
                "created": 0,
                "matched_users": 0,
                "emails_sent": 0,
                "emails_skipped": 0,
                "emails_failed": 0,
            }

        # 仅对中/高风险生成自选提醒；5%涨幅池这类低风险观察标签不打扰用户
        risk_items = [
            item for item in risk_items
            if str(item.get("risk_level") or "") in ("high", "medium")
        ]
        if not risk_items:
            return {
                "trade_date": effective_date,
                "created": 0,
                "matched_users": 0,
                "emails_sent": 0,
                "emails_skipped": 0,
                "emails_failed": 0,
            }

        risk_by_code = {item["ts_code"]: item for item in risk_items}
        codes = list(risk_by_code.keys())
        placeholders = ",".join("?" for _ in codes)
        now = datetime.utcnow().isoformat() + "Z"
        created = 0
        matched_users = set()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT DISTINCT w.user_id, wi.ts_code, wi.name
                FROM watchlist_items wi
                JOIN watchlists w ON w.id = wi.watchlist_id
                WHERE wi.ts_code IN ({placeholders})
                """,
                codes,
            )
            rows = [dict(row) for row in cursor.fetchall()]

            for row in rows:
                ts_code = row.get("ts_code")
                user_id = row.get("user_id")
                if not ts_code or not user_id:
                    continue
                risk_item = risk_by_code.get(ts_code)
                if not risk_item:
                    continue

                tags = self._parse_tags(risk_item.get("tags_json"))
                cursor.execute(
                    """
                    INSERT INTO watchlist_risk_alerts (
                        id, user_id, ts_code, stock_name, trade_date,
                        tags_json, risk_level, reason, created_at, read_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    ON CONFLICT(user_id, ts_code, trade_date) DO NOTHING
                    """,
                    (
                        f"wra_{uuid.uuid4().hex[:12]}",
                        user_id,
                        ts_code,
                        row.get("name") or risk_item.get("name") or ts_code,
                        effective_date,
                        json.dumps(tags, ensure_ascii=False),
                        risk_item.get("risk_level") or "high",
                        risk_item.get("reason") or "",
                        now,
                    ),
                )
                if cursor.rowcount > 0:
                    created += 1
                    matched_users.add(user_id)
            conn.commit()

        logger.info(
            f"[WatchlistRiskAlert] trade_date={effective_date} created={created} users={len(matched_users)}"
        )
        email_result = self._send_email_digests(effective_date)
        return {
            "trade_date": effective_date,
            "created": created,
            "matched_users": len(matched_users),
            "emails_sent": email_result.get("sent", 0),
            "emails_skipped": email_result.get("skipped", 0),
            "emails_failed": email_result.get("failed", 0),
        }

    def _send_email_digests(self, trade_date: str) -> Dict[str, Any]:
        try:
            from services.risk_alert_email_service import RiskAlertEmailService

            return RiskAlertEmailService().send_digests_for_trade_date(trade_date)
        except Exception as exc:
            logger.warning(f"[WatchlistRiskAlert] risk alert email dispatch failed: {exc}")
            return {"sent": 0, "skipped": 0, "failed": 0}

    def get_unread_count(self, user_id: str) -> int:
        if not user_id:
            return 0
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS c
                FROM watchlist_risk_alerts
                WHERE user_id = ? AND read_at IS NULL
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        return int(row.get("c") or 0) if row else 0

    def list_alerts(self, user_id: str, limit: int = 20, unread_only: bool = False) -> Dict[str, Any]:
        limit = min(max(int(limit or 20), 1), 100)
        if not user_id:
            return {"unread_count": 0, "items": []}

        unread_count = self.get_unread_count(user_id)
        query = """
            SELECT *
            FROM watchlist_risk_alerts
            WHERE user_id = ?
        """
        params: List[Any] = [user_id]
        if unread_only:
            query += " AND read_at IS NULL"
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = [self._serialize_alert(dict(row)) for row in cursor.fetchall()]

        return {"unread_count": unread_count, "items": rows}

    def mark_all_read(self, user_id: str) -> Dict[str, Any]:
        if not user_id:
            return {"updated": 0}
        now = datetime.utcnow().isoformat() + "Z"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE watchlist_risk_alerts
                SET read_at = ?
                WHERE user_id = ? AND read_at IS NULL
                """,
                (now, user_id),
            )
            updated = cursor.rowcount
            conn.commit()
        return {"updated": updated}

    def _serialize_alert(self, row: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(row)
        item["tags"] = self._parse_tags(item.get("tags_json"))
        return item

    def _parse_tags(self, raw_tags: Any) -> List[str]:
        if isinstance(raw_tags, list):
            return raw_tags
        try:
            parsed = json.loads(raw_tags or "[]")
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
