"""
Digest email when judgment records enter due status (待复盘提醒).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from auth.dependencies import ALGORITHM, SECRET_KEY
from database.db_factory import DatabaseFactory
from jose import jwt
from services.email_service import send_journal_due_digest
from services.notify_pref_service import NotifyPrefService
from services.user_service import UserService
from utils.logger import get_logger

logger = get_logger()

SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://aguai.net").rstrip("/")
UNSUBSCRIBE_TOKEN_DAYS = 365
SHANGHAI = ZoneInfo("Asia/Shanghai")


def _digest_date_label() -> str:
    return datetime.now(SHANGHAI).date().isoformat()


def create_journal_due_unsubscribe_token(user_id: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "purpose": "journal_due_unsubscribe",
        "iat": now,
        "exp": now + timedelta(days=UNSUBSCRIBE_TOKEN_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_journal_due_unsubscribe_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None
    if payload.get("purpose") != "journal_due_unsubscribe":
        return None
    user_id = str(payload.get("sub") or "").strip()
    return user_id or None


class JournalDueEmailService:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            DatabaseFactory.initialize(db_path)
        self.db = DatabaseFactory
        self.user_service = UserService(db_path=db_path)
        self.notify_pref_service = NotifyPrefService(db_path=db_path)

    def send_daily_digests(self, digest_date: Optional[str] = None) -> Dict[str, Any]:
        digest_date = digest_date or _digest_date_label()
        user_ids = self._users_with_due_records()
        sent = 0
        skipped = 0
        failed = 0

        for user_id in user_ids:
            result = self._send_digest_for_user(user_id, digest_date)
            status = result.get("status")
            if status == "sent":
                sent += 1
            elif status == "failed":
                failed += 1
            else:
                skipped += 1

        logger.info(
            f"[JournalDueEmail] digest_date={digest_date} sent={sent} skipped={skipped} failed={failed}"
        )
        return {
            "digest_date": digest_date,
            "sent": sent,
            "skipped": skipped,
            "failed": failed,
        }

    def _users_with_due_records(self) -> List[str]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT user_id
                FROM judgments
                WHERE status = 'due'
                ORDER BY user_id
                """
            )
            return [str(row.get("user_id")) for row in cursor.fetchall() if row.get("user_id")]

    def _already_sent(self, user_id: str, digest_date: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT status
                FROM journal_due_email_log
                WHERE user_id = ? AND digest_date = ?
                """,
                (user_id, digest_date),
            )
            row = cursor.fetchone()
        return bool(row and row.get("status") == "sent")

    def _get_due_records_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, stock_code, candidate, created_at, validation_date, snapshot
                FROM judgments
                WHERE user_id = ? AND status = 'due'
                ORDER BY validation_date ASC, created_at ASC
                LIMIT 20
                """,
                (user_id,),
            )
            rows = [dict(row) for row in cursor.fetchall()]

        items: List[Dict[str, Any]] = []
        for row in rows:
            stock_name = self._extract_stock_name(row.get("snapshot"), row.get("stock_code"))
            items.append(
                {
                    "id": row.get("id"),
                    "ts_code": row.get("stock_code"),
                    "stock_name": stock_name,
                    "candidate": row.get("candidate"),
                    "created_at": row.get("created_at"),
                    "validation_date": row.get("validation_date"),
                }
            )
        return items

    def _send_digest_for_user(self, user_id: str, digest_date: str) -> Dict[str, Any]:
        if self._already_sent(user_id, digest_date):
            return {"status": "skipped", "reason": "already_sent"}

        if not self.notify_pref_service.is_journal_due_email_enabled(user_id):
            self._record_log(user_id, digest_date, "", 0, "skipped", "notify_pref_disabled")
            return {"status": "skipped", "reason": "notify_pref_disabled"}

        user = self.user_service.get_user(user_id) or {}
        email = str(user.get("primary_email") or "").strip().lower()
        if not email or not int(user.get("email_verified") or 0):
            self._record_log(user_id, digest_date, email, 0, "skipped", "no_verified_email")
            return {"status": "skipped", "reason": "no_verified_email"}

        due_records = self._get_due_records_for_user(user_id)
        if not due_records:
            return {"status": "skipped", "reason": "no_due_records"}

        unsubscribe_url = (
            f"{SITE_BASE_URL}/api/v1/notifications/unsubscribe-journal-due"
            f"?token={create_journal_due_unsubscribe_token(user_id)}"
        )
        journal_url = f"{SITE_BASE_URL}/journal?status=due"
        ok, message = send_journal_due_digest(
            email=email,
            digest_date=digest_date,
            due_records=due_records,
            journal_url=journal_url,
            unsubscribe_url=unsubscribe_url,
            site_base_url=SITE_BASE_URL,
        )
        if ok:
            self._record_log(user_id, digest_date, email, len(due_records), "sent", None)
            return {"status": "sent", "message": message}

        self._record_log(user_id, digest_date, email, len(due_records), "failed", message)
        return {"status": "failed", "message": message}

    def _record_log(
        self,
        user_id: str,
        digest_date: str,
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
                INSERT INTO journal_due_email_log (
                    user_id, digest_date, email, item_count, status, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, digest_date) DO UPDATE SET
                    email = excluded.email,
                    item_count = excluded.item_count,
                    status = excluded.status,
                    error_message = excluded.error_message,
                    created_at = excluded.created_at
                """,
                (user_id, digest_date, email, item_count, status, error_message, now),
            )
            conn.commit()

    def _extract_stock_name(self, raw_snapshot: Any, ts_code: Any) -> str:
        snapshot = raw_snapshot
        if isinstance(raw_snapshot, str):
            try:
                snapshot = json.loads(raw_snapshot)
            except Exception:
                snapshot = {}
        if isinstance(snapshot, dict):
            summary = snapshot.get("watchlist_summary") or {}
            name = summary.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        return str(ts_code or "").strip()
