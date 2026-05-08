"""
Runtime key/value settings stored in SQLite (app_settings).
Used for AI URL/model/timeout overrides; secrets like API_KEY stay in environment only.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Optional

from database.db_factory import DatabaseFactory
from utils.logger import get_logger

logger = get_logger()

# Keys the admin API may write (allowlist)
PATCHABLE_KEYS = frozenset({"ai.api_url", "ai.api_model", "ai.api_timeout"})


class AppSettingsService:
    def __init__(self, db_path: str | None = None):
        self.db = DatabaseFactory
        if db_path:
            DatabaseFactory.initialize(db_path)

    def get(self, key: str) -> Optional[str]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row and row.get("value") is not None else None

    def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        if not keys:
            return {}
        placeholders = ",".join("?" * len(keys))
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT key, value FROM app_settings WHERE key IN ({placeholders})",
                keys,
            )
            rows = cur.fetchall()
        out = {k: None for k in keys}
        for r in rows:
            out[r["key"]] = r.get("value")
        return out

    def list_all(self) -> List[Dict[str, str]]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT key, value, updated_at FROM app_settings ORDER BY key")
            return [dict(r) for r in cur.fetchall()]

    def upsert(self, key: str, value: str) -> None:
        if key not in PATCHABLE_KEYS:
            raise ValueError(f"key not allowed: {key}")
        now = datetime.utcnow().isoformat() + "Z"
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
            conn.commit()

    def patch_many(self, updates: Dict[str, str]) -> None:
        for k, v in updates.items():
            if k not in PATCHABLE_KEYS:
                raise ValueError(f"key not allowed: {k}")
            if v is None:
                continue
            self.upsert(k, str(v).strip())


def ai_runtime_overrides() -> Dict[str, Optional[str]]:
    """Read AI-related overrides from DB (empty string treated as unset)."""
    svc = AppSettingsService()
    raw = svc.get_many(["ai.api_url", "ai.api_model", "ai.api_timeout"])
    return {
        "api_url": (raw.get("ai.api_url") or "").strip() or None,
        "api_model": (raw.get("ai.api_model") or "").strip() or None,
        "api_timeout": (raw.get("ai.api_timeout") or "").strip() or None,
    }


def ai_effective_for_admin_display() -> Dict[str, str]:
    """
    Resolved AI URL / model / timeout for admin UI (same merge order as AIAnalyzer: DB then env).
    """
    ov = ai_runtime_overrides()
    url = (ov.get("api_url") or "").strip() or (os.getenv("API_URL") or "").strip()
    model = (ov.get("api_model") or "").strip() or (os.getenv("API_MODEL") or "deepseek-reasoner").strip()
    timeout_raw = (ov.get("api_timeout") or "").strip() or (os.getenv("API_TIMEOUT") or "60")
    try:
        timeout_out = str(int(timeout_raw))
    except (TypeError, ValueError):
        timeout_out = str(timeout_raw)
    return {
        "ai.api_url": url,
        "ai.api_model": model,
        "ai.api_timeout": timeout_out,
    }
