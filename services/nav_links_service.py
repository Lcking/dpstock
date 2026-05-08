"""Nav header links stored in SQLite."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db_factory import DatabaseFactory
from utils.logger import get_logger

logger = get_logger()


class NavLinksService:
    def __init__(self, db_path: str | None = None):
        self.db = DatabaseFactory
        if db_path:
            DatabaseFactory.initialize(db_path)

    def list_public(self) -> List[Dict[str, Any]]:
        """Enabled links for /api/config (frontend NavBar)."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, label, href, target, rel, sort_order
                FROM nav_links
                WHERE enabled = 1
                ORDER BY sort_order ASC, id ASC
                """
            )
            return [dict(r) for r in cur.fetchall()]

    def list_all(self) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, label, href, target, rel, sort_order, enabled, created_at, updated_at "
                "FROM nav_links ORDER BY sort_order ASC, id ASC"
            )
            return [dict(r) for r in cur.fetchall()]

    def get(self, link_id: int) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM nav_links WHERE id = ?", (link_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def create(
        self,
        *,
        label: str,
        href: str,
        target: str = "_blank",
        rel: str = "noopener",
        sort_order: int = 0,
        enabled: int = 1,
    ) -> int:
        now = datetime.utcnow().isoformat() + "Z"
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO nav_links (label, href, target, rel, sort_order, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (label.strip(), href.strip(), target or "_blank", rel or "noopener", sort_order, enabled, now, now),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update(self, link_id: int, fields: Dict[str, Any]) -> bool:
        allowed = {"label", "href", "target", "rel", "sort_order", "enabled"}
        sets = []
        vals: List[Any] = []
        for k, v in fields.items():
            if k not in allowed:
                continue
            sets.append(f"{k} = ?")
            vals.append(v)
        if not sets:
            return False
        now = datetime.utcnow().isoformat() + "Z"
        sets.append("updated_at = ?")
        vals.append(now)
        vals.append(link_id)
        sql = f"UPDATE nav_links SET {', '.join(sets)} WHERE id = ?"
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, vals)
            conn.commit()
            return cur.rowcount > 0

    def delete(self, link_id: int) -> bool:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM nav_links WHERE id = ?", (link_id,))
            conn.commit()
            return cur.rowcount > 0
