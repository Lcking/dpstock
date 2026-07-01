"""
User notification preference helpers.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from database.db_factory import DatabaseFactory
from utils.logger import get_logger

logger = get_logger()

DEFAULT_NOTIFY_PREF: Dict[str, bool] = {
    "risk_alert_email": True,
    "journal_due_email": True,
}


def parse_notify_pref(raw_value: Any) -> Dict[str, bool]:
    if isinstance(raw_value, dict):
        data = raw_value
    else:
        try:
            data = json.loads(raw_value or "{}")
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    return {
        "risk_alert_email": bool(data.get("risk_alert_email", DEFAULT_NOTIFY_PREF["risk_alert_email"])),
        "journal_due_email": bool(data.get("journal_due_email", DEFAULT_NOTIFY_PREF["journal_due_email"])),
    }


def serialize_notify_pref(pref: Dict[str, bool]) -> str:
    normalized = parse_notify_pref(pref)
    return json.dumps(normalized, ensure_ascii=False)


class NotifyPrefService:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            DatabaseFactory.initialize(db_path)
        self.db = DatabaseFactory

    def get_notify_pref(self, user_id: str) -> Dict[str, bool]:
        if not user_id:
            return dict(DEFAULT_NOTIFY_PREF)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                row = cursor.execute(
                    "SELECT notify_pref FROM users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
            except Exception:
                return dict(DEFAULT_NOTIFY_PREF)
        if not row:
            return dict(DEFAULT_NOTIFY_PREF)
        return parse_notify_pref(row.get("notify_pref"))

    def is_risk_alert_email_enabled(self, user_id: str) -> bool:
        return self.get_notify_pref(user_id).get("risk_alert_email", True)

    def is_journal_due_email_enabled(self, user_id: str) -> bool:
        return self.get_notify_pref(user_id).get("journal_due_email", True)

    def _save_notify_pref(self, user_id: str, pref: Dict[str, bool]) -> Dict[str, bool]:
        normalized = parse_notify_pref(pref)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE users
                SET notify_pref = ?
                WHERE user_id = ?
                """,
                (serialize_notify_pref(normalized), user_id),
            )
            conn.commit()
        return normalized

    def set_risk_alert_email(self, user_id: str, enabled: bool) -> Dict[str, bool]:
        if not user_id:
            raise ValueError("user_id is required")
        pref = self.get_notify_pref(user_id)
        pref["risk_alert_email"] = bool(enabled)
        saved = self._save_notify_pref(user_id, pref)
        logger.info(
            f"[NotifyPref] user={user_id} risk_alert_email={saved['risk_alert_email']}"
        )
        return saved

    def set_journal_due_email(self, user_id: str, enabled: bool) -> Dict[str, bool]:
        if not user_id:
            raise ValueError("user_id is required")
        pref = self.get_notify_pref(user_id)
        pref["journal_due_email"] = bool(enabled)
        saved = self._save_notify_pref(user_id, pref)
        logger.info(
            f"[NotifyPref] user={user_id} journal_due_email={saved['journal_due_email']}"
        )
        return saved

    def update_notify_pref(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, bool]:
        pref = self.get_notify_pref(user_id)
        if "risk_alert_email" in updates:
            pref["risk_alert_email"] = bool(updates["risk_alert_email"])
        if "journal_due_email" in updates:
            pref["journal_due_email"] = bool(updates["journal_due_email"])
        return self._save_notify_pref(user_id, pref)
