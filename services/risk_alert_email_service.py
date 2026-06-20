"""
Risk alert email digest delivery for watchlist hits.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from auth.dependencies import SECRET_KEY, ALGORITHM
from database.db_factory import DatabaseFactory
from jose import jwt
from services.email_service import send_risk_alert_digest
from services.notify_pref_service import NotifyPrefService
from services.user_service import UserService
from utils.logger import get_logger

logger = get_logger()

SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://aguai.net").rstrip("/")
UNSUBSCRIBE_TOKEN_DAYS = 365


def create_risk_alert_unsubscribe_token(user_id: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "purpose": "risk_alert_unsubscribe",
        "iat": now,
        "exp": now + timedelta(days=UNSUBSCRIBE_TOKEN_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_risk_alert_unsubscribe_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None
    if payload.get("purpose") != "risk_alert_unsubscribe":
        return None
    user_id = str(payload.get("sub") or "").strip()
    return user_id or None


class RiskAlertEmailService:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            DatabaseFactory.initialize(db_path)
        self.db = DatabaseFactory
        self.user_service = UserService(db_path=db_path)
        self.notify_pref_service = NotifyPrefService(db_path=db_path)

    def send_digests_for_trade_date(self, trade_date: str) -> Dict[str, Any]:
        if not trade_date:
            return {"trade_date": None, "sent": 0, "skipped": 0, "failed": 0}

        user_ids = self._users_with_alerts(trade_date)
        sent = 0
        skipped = 0
        failed = 0

        for user_id in user_ids:
            result = self._send_digest_for_user(user_id, trade_date)
            status = result.get("status")
            if status == "sent":
                sent += 1
            elif status == "failed":
                failed += 1
            else:
                skipped += 1

        logger.info(
            f"[RiskAlertEmail] trade_date={trade_date} sent={sent} skipped={skipped} failed={failed}"
        )
        return {
            "trade_date": trade_date,
            "sent": sent,
            "skipped": skipped,
            "failed": failed,
        }

    def _users_with_alerts(self, trade_date: str) -> List[str]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT user_id
                FROM watchlist_risk_alerts
                WHERE trade_date = ?
                ORDER BY user_id
                """,
                (trade_date,),
            )
            return [str(row.get("user_id")) for row in cursor.fetchall() if row.get("user_id")]

    def _already_sent(self, user_id: str, trade_date: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT status
                FROM risk_alert_email_log
                WHERE user_id = ? AND trade_date = ?
                """,
                (user_id, trade_date),
            )
            row = cursor.fetchone()
        return bool(row and row.get("status") == "sent")

    def _get_alerts_for_user(self, user_id: str, trade_date: str) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT stock_name, ts_code, tags_json, risk_level, reason
                FROM watchlist_risk_alerts
                WHERE user_id = ? AND trade_date = ?
                ORDER BY created_at ASC
                """,
                (user_id, trade_date),
            )
            rows = [dict(row) for row in cursor.fetchall()]

        items = []
        for row in rows:
            tags = self._parse_tags(row.get("tags_json"))
            items.append(
                {
                    "stock_name": row.get("stock_name") or row.get("ts_code"),
                    "ts_code": row.get("ts_code"),
                    "tags": tags,
                    "risk_level": row.get("risk_level") or "high",
                    "reason": row.get("reason") or "",
                }
            )
        return items

    def _send_digest_for_user(self, user_id: str, trade_date: str) -> Dict[str, Any]:
        if self._already_sent(user_id, trade_date):
            return {"status": "skipped", "reason": "already_sent"}

        if not self.notify_pref_service.is_risk_alert_email_enabled(user_id):
            self._record_log(user_id, trade_date, "", 0, "skipped", "notify_pref_disabled")
            return {"status": "skipped", "reason": "notify_pref_disabled"}

        user = self.user_service.get_user(user_id) or {}
        email = str(user.get("primary_email") or "").strip().lower()
        if not email or not int(user.get("email_verified") or 0):
            self._record_log(user_id, trade_date, email, 0, "skipped", "no_verified_email")
            return {"status": "skipped", "reason": "no_verified_email"}

        alerts = self._get_alerts_for_user(user_id, trade_date)
        if not alerts:
            return {"status": "skipped", "reason": "no_alerts"}

        unsubscribe_url = (
            f"{SITE_BASE_URL}/api/v1/notifications/unsubscribe"
            f"?token={create_risk_alert_unsubscribe_token(user_id)}"
        )
        ok, message = send_risk_alert_digest(
            email=email,
            trade_date=trade_date,
            alerts=alerts,
            unsubscribe_url=unsubscribe_url,
            site_base_url=SITE_BASE_URL,
        )
        if ok:
            self._record_log(user_id, trade_date, email, len(alerts), "sent", None)
            return {"status": "sent", "message": message}

        self._record_log(user_id, trade_date, email, len(alerts), "failed", message)
        return {"status": "failed", "message": message}

    def _record_log(
        self,
        user_id: str,
        trade_date: str,
        email: str,
        item_count: int,
        status: str,
        error_message: Optional[str],
    ) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO risk_alert_email_log (
                    user_id, trade_date, email, item_count, status, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, trade_date) DO UPDATE SET
                    email = excluded.email,
                    item_count = excluded.item_count,
                    status = excluded.status,
                    error_message = excluded.error_message,
                    created_at = excluded.created_at
                """,
                (user_id, trade_date, email, item_count, status, error_message, now),
            )
            conn.commit()

    def _parse_tags(self, raw_tags: Any) -> List[str]:
        if isinstance(raw_tags, list):
            return raw_tags
        try:
            import json

            parsed = json.loads(raw_tags or "[]")
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
