"""
Unified user service.

Phase 1 Task 1 only introduces a stable user_id plus identity mapping.
Existing routes can adopt this service incrementally in later tasks.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import Optional, Iterable

from database.db_factory import DatabaseFactory
from utils.logger import get_logger

logger = get_logger()


class UserService:
    def __init__(self, db_path: Optional[str] = None):
        self.db = DatabaseFactory()
        if db_path:
            DatabaseFactory.initialize(db_path)

    def _get_db(self) -> sqlite3.Connection:
        return self.db.get_connection()

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()

    @staticmethod
    def _normalize_identity(identity_type: str, identity_value: str) -> tuple[str, str]:
        normalized_type = (identity_type or "").strip()
        normalized_value = (identity_value or "").strip()
        if not normalized_type or not normalized_value:
            raise ValueError("identity_type and identity_value are required")
        return normalized_type, normalized_value

    @staticmethod
    def _unique_non_empty(values: Iterable[Optional[str]]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if not value:
                continue
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result

    @staticmethod
    def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
        row = cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
            (table_name,),
        ).fetchone()
        return row is not None

    def get_user(self, user_id: str) -> Optional[dict]:
        db = self._get_db()
        cursor = db.cursor()
        try:
            row = cursor.execute(
                """
                SELECT
                    user_id,
                    primary_email,
                    email_verified,
                    display_name,
                    profile_completed,
                    is_public_analysis_enabled,
                    status,
                    created_at,
                    last_active_at
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            db.close()

    def is_temporary_user(self, user_id: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return True
        return not bool(user.get("email_verified") or user.get("primary_email"))

    def resolve_identity(self, identity_type: str, identity_value: str) -> Optional[str]:
        identity_type, identity_value = self._normalize_identity(identity_type, identity_value)
        db = self._get_db()
        cursor = db.cursor()
        try:
            row = cursor.execute(
                """
                SELECT user_id
                FROM user_identities
                WHERE identity_type = ? AND identity_value = ?
                LIMIT 1
                """,
                (identity_type, identity_value),
            ).fetchone()
            return row.get("user_id") if row else None
        finally:
            db.close()

    def create_user(
        self,
        *,
        primary_email: Optional[str] = None,
        email_verified: bool = False,
        display_name: Optional[str] = None,
    ) -> str:
        user_id = str(uuid.uuid4())
        now = self._now()
        db = self._get_db()
        cursor = db.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (
                    user_id,
                    primary_email,
                    email_verified,
                    display_name,
                    profile_completed,
                    is_public_analysis_enabled,
                    status,
                    created_at,
                    last_active_at
                )
                VALUES (?, ?, ?, ?, 0, 0, 'active', ?, ?)
                """,
                (
                    user_id,
                    primary_email,
                    1 if email_verified else 0,
                    display_name,
                    now,
                    now,
                ),
            )
            db.commit()
            return user_id
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def attach_identity(
        self,
        *,
        user_id: str,
        identity_type: str,
        identity_value: str,
        is_primary: bool = False,
        verified_at: Optional[str] = None,
    ) -> None:
        identity_type, identity_value = self._normalize_identity(identity_type, identity_value)
        now = self._now()
        db = self._get_db()
        cursor = db.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO user_identities (
                    identity_type,
                    identity_value,
                    user_id,
                    is_primary,
                    verified_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(identity_type, identity_value)
                DO UPDATE SET
                    user_id = excluded.user_id,
                    is_primary = excluded.is_primary,
                    verified_at = COALESCE(excluded.verified_at, user_identities.verified_at),
                    updated_at = excluded.updated_at
                """,
                (
                    identity_type,
                    identity_value,
                    user_id,
                    1 if is_primary else 0,
                    verified_at,
                    now,
                    now,
                ),
            )
            cursor.execute(
                "UPDATE users SET last_active_at = ? WHERE user_id = ?",
                (now, user_id),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_or_create_user_by_identity(self, *, identity_type: str, identity_value: str) -> str:
        identity_type, identity_value = self._normalize_identity(identity_type, identity_value)
        existing_user_id = self.resolve_identity(identity_type, identity_value)
        if existing_user_id:
            logger.debug(f"[UserService] Resolved existing identity {identity_type}:{identity_value}")
            return existing_user_id

        user_id = self.create_user()
        self.attach_identity(
            user_id=user_id,
            identity_type=identity_type,
            identity_value=identity_value,
            is_primary=True,
        )
        logger.info(f"[UserService] Created user {user_id} for identity {identity_type}")
        return user_id

    def _move_user_owned_rows(
        self,
        cursor: sqlite3.Cursor,
        *,
        table_name: str,
        column_name: str,
        from_value: str,
        to_value: str,
    ) -> None:
        if from_value == to_value or not self._table_exists(cursor, table_name):
            return
        cursor.execute(
            f"UPDATE OR IGNORE {table_name} SET {column_name} = ? WHERE {column_name} = ?",
            (to_value, from_value),
        )
        cursor.execute(
            f"DELETE FROM {table_name} WHERE {column_name} = ?",
            (from_value,),
        )

    def _move_invite_codes(
        self,
        cursor: sqlite3.Cursor,
        *,
        from_value: str,
        to_value: str,
    ) -> None:
        if from_value == to_value or not self._table_exists(cursor, "invite_codes"):
            return
        existing = cursor.execute(
            "SELECT 1 FROM invite_codes WHERE inviter_id = ? LIMIT 1",
            (to_value,),
        ).fetchone()
        if existing:
            cursor.execute("DELETE FROM invite_codes WHERE inviter_id = ?", (from_value,))
            return
        cursor.execute(
            "UPDATE invite_codes SET inviter_id = ? WHERE inviter_id = ?",
            (to_value, from_value),
        )

    def _merge_assets_into_user(
        self,
        cursor: sqlite3.Cursor,
        *,
        from_value: str,
        to_user_id: str,
    ) -> None:
        if not from_value or from_value == to_user_id:
            return
        self._move_user_owned_rows(
            cursor,
            table_name="judgments",
            column_name="user_id",
            from_value=from_value,
            to_value=to_user_id,
        )
        self._move_user_owned_rows(
            cursor,
            table_name="watchlists",
            column_name="user_id",
            from_value=from_value,
            to_value=to_user_id,
        )
        self._move_user_owned_rows(
            cursor,
            table_name="analysis_records",
            column_name="user_id",
            from_value=from_value,
            to_value=to_user_id,
        )
        self._move_invite_codes(cursor, from_value=from_value, to_value=to_user_id)
        self._move_user_owned_rows(
            cursor,
            table_name="invite_rewards",
            column_name="inviter_id",
            from_value=from_value,
            to_value=to_user_id,
        )
        self._move_user_owned_rows(
            cursor,
            table_name="invite_rewards",
            column_name="invitee_id",
            from_value=from_value,
            to_value=to_user_id,
        )

    def migrate_identities_to_user(
        self,
        *,
        user_id: str,
        anonymous_id: Optional[str] = None,
        cookie_uid: Optional[str] = None,
        anchor_id: Optional[str] = None,
    ) -> None:
        db = self._get_db()
        cursor = db.cursor()
        try:
            for from_value in self._unique_non_empty([anonymous_id, cookie_uid, anchor_id]):
                self._merge_assets_into_user(
                    cursor,
                    from_value=from_value,
                    to_user_id=user_id,
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def bind_email_identity(
        self,
        *,
        anonymous_id: Optional[str] = None,
        cookie_uid: Optional[str] = None,
        anchor_id: str,
        email: str,
    ) -> str:
        normalized_email = (email or "").strip().lower()
        if not normalized_email:
            raise ValueError("email is required")

        identities = [
            ("anonymous", anonymous_id),
            ("cookie_uid", cookie_uid),
            ("email_anchor", anchor_id),
        ]
        normalized_identities = [
            self._normalize_identity(identity_type, identity_value)
            for identity_type, identity_value in identities
            if identity_value
        ]
        if not normalized_identities:
            raise ValueError("at least one identity is required")

        existing_user_ids = []
        for identity_type, identity_value in normalized_identities:
            resolved = self.resolve_identity(identity_type, identity_value)
            if resolved and resolved not in existing_user_ids:
                existing_user_ids.append(resolved)

        target_user_id = existing_user_ids[0] if existing_user_ids else self.create_user(
            primary_email=normalized_email,
            email_verified=True,
        )

        now = self._now()
        db = self._get_db()
        cursor = db.cursor()
        try:
            for from_value in self._unique_non_empty([anonymous_id, cookie_uid, anchor_id, *existing_user_ids]):
                self._merge_assets_into_user(
                    cursor,
                    from_value=from_value,
                    to_user_id=target_user_id,
                )

            cursor.execute(
                """
                UPDATE users
                SET primary_email = ?,
                    email_verified = 1,
                    last_active_at = ?
                WHERE user_id = ?
                """,
                (normalized_email, now, target_user_id),
            )

            for identity_type, identity_value in normalized_identities:
                cursor.execute(
                    """
                    INSERT INTO user_identities (
                        identity_type,
                        identity_value,
                        user_id,
                        is_primary,
                        verified_at,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(identity_type, identity_value)
                    DO UPDATE SET
                        user_id = excluded.user_id,
                        is_primary = excluded.is_primary,
                        verified_at = COALESCE(excluded.verified_at, user_identities.verified_at),
                        updated_at = excluded.updated_at
                    """,
                    (
                        identity_type,
                        identity_value,
                        target_user_id,
                        1 if identity_type == "email_anchor" else 0,
                        now if identity_type == "email_anchor" else None,
                        now,
                        now,
                    ),
                )

            for existing_user_id in existing_user_ids:
                if existing_user_id == target_user_id:
                    continue
                cursor.execute("DELETE FROM users WHERE user_id = ?", (existing_user_id,))

            db.commit()
            logger.info(
                f"[UserService] Bound email identity to unified user {target_user_id}"
            )
            return target_user_id
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def resolve_request_user(
        self,
        *,
        anchor_id: Optional[str] = None,
        anonymous_id: Optional[str] = None,
        cookie_uid: Optional[str] = None,
        create_missing_cookie: bool = False,
    ) -> dict:
        if anchor_id:
            user_id = self.get_or_create_user_by_identity(
                identity_type="email_anchor",
                identity_value=anchor_id,
            )
            return {
                "user_id": user_id,
                "identity_type": "email_anchor",
                "identity_value": anchor_id,
                "created_cookie_uid": None,
            }

        if anonymous_id:
            user_id = self.get_or_create_user_by_identity(
                identity_type="anonymous",
                identity_value=anonymous_id,
            )
            return {
                "user_id": user_id,
                "identity_type": "anonymous",
                "identity_value": anonymous_id,
                "created_cookie_uid": None,
            }

        if cookie_uid:
            user_id = self.get_or_create_user_by_identity(
                identity_type="cookie_uid",
                identity_value=cookie_uid,
            )
            return {
                "user_id": user_id,
                "identity_type": "cookie_uid",
                "identity_value": cookie_uid,
                "created_cookie_uid": None,
            }

        if not create_missing_cookie:
            raise ValueError("no identity provided")

        created_cookie_uid = str(uuid.uuid4())
        user_id = self.get_or_create_user_by_identity(
            identity_type="cookie_uid",
            identity_value=created_cookie_uid,
        )
        return {
            "user_id": user_id,
            "identity_type": "cookie_uid",
            "identity_value": created_cookie_uid,
            "created_cookie_uid": created_cookie_uid,
        }
