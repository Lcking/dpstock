"""
Persist site-wide and per-IP analyze limits.

The global counter is the spend ceiling: every stock in a request reserves
one slot before the model is called, including repeats. Anonymous new-stock
quota is keyed by client IP, not by a client-supplied anonymous id.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date
from typing import Dict, List, Optional, Tuple

from database.db_factory import DatabaseFactory
from database.sqlite_utils import run_with_busy_retry
from services.quota_service import QuotaService
from utils.logger import get_logger

logger = get_logger()

_DEFAULT_GLOBAL_DAILY_MAX = 40


class SpendGuardUnavailable(RuntimeError):
    """The limit store could not be read or updated. Callers must not call the model."""


class AnalyzeSpendGuard:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("DB_PATH", "data/stocks.db")
        DatabaseFactory.initialize(self.db_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with DatabaseFactory.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyze_global_daily (
                    usage_date TEXT PRIMARY KEY,
                    stock_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyze_ip_daily (
                    usage_date TEXT NOT NULL,
                    client_ip TEXT NOT NULL,
                    stock_code TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (usage_date, client_ip, stock_code)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analyze_ip_daily_ip
                ON analyze_ip_daily(usage_date, client_ip)
                """
            )
            conn.commit()

    @staticmethod
    def global_daily_max() -> int:
        raw = os.getenv("ANALYZE_GLOBAL_DAILY_MAX", str(_DEFAULT_GLOBAL_DAILY_MAX))
        try:
            return max(int(raw), 0)
        except (TypeError, ValueError):
            return _DEFAULT_GLOBAL_DAILY_MAX

    @staticmethod
    def anonymous_base_quota() -> int:
        raw = os.getenv("ANALYZE_QUOTA_ANONYMOUS", str(QuotaService.ANONYMOUS_BASE_QUOTA))
        try:
            return max(int(raw), 0)
        except (TypeError, ValueError):
            return QuotaService.ANONYMOUS_BASE_QUOTA

    def status(self, *, client_ip: str, user_id: str) -> Dict:
        """Anonymous quota as shown in the UI. Usage follows the client IP."""
        today = date.today().isoformat()
        invite_quota = self._invite_quota(user_id)
        base_quota = self.anonymous_base_quota()
        total_quota = base_quota + invite_quota
        try:
            seen = self._seen_codes(today, client_ip)
        except sqlite3.Error as exc:
            logger.error(f"[AnalyzeSpend] status read failed: {exc}")
            seen = []
        used = len(seen)
        return {
            "user_id": user_id,
            "date": today,
            "base_quota": base_quota,
            "invite_quota": invite_quota,
            "total_quota": total_quota,
            "used_quota": used,
            "remaining_quota": max(0, total_quota - used),
            "analyzed_stocks_today": seen,
            "is_authenticated": False,
        }

    def peek(
        self,
        *,
        client_ip: str,
        stock_code: str,
        user_id: str,
    ) -> Tuple[bool, str, Dict]:
        """Dry-run the anonymous IP quota. Does not reserve a global slot."""
        code = str(stock_code or "").strip()
        if not code:
            return False, "invalid_request", {"message": "请输入代码"}
        snapshot = self.status(client_ip=client_ip, user_id=user_id)
        if code in snapshot["analyzed_stocks_today"]:
            return True, "history", {
                "message": "这是您今日已分析过的股票,可以重复查看",
                "remaining_quota": snapshot["remaining_quota"],
            }
        if snapshot["remaining_quota"] > 0:
            return True, "quota_available", {
                "remaining_quota": snapshot["remaining_quota"],
                "message": f"可以分析,剩余 {snapshot['remaining_quota']} 次新股票额度",
            }
        return False, "quota_exceeded", {
            "remaining_quota": 0,
            "required_quota": 1,
            "total_quota": snapshot["total_quota"],
            "analyzed_stocks_today": snapshot["analyzed_stocks_today"],
            "message": self._ip_quota_message(snapshot),
        }

    def reserve(
        self,
        *,
        client_ip: str,
        stock_codes: List[str],
        enforce_ip_quota: bool,
        ip_extra_quota: int = 0,
        user_id: str = "",
    ) -> Tuple[bool, str, Dict]:
        """
        Atomically reserve model calls.

        Returns (allowed, reason, details). Raises SpendGuardUnavailable when
        the counter cannot be updated; callers must not call the model.
        """
        codes = list(dict.fromkeys(str(code).strip() for code in stock_codes if str(code).strip()))
        if not codes:
            return False, "invalid_request", {"message": "请输入代码"}

        today = date.today().isoformat()
        global_max = self.global_daily_max()
        ip_limit = self.anonymous_base_quota() + max(int(ip_extra_quota or 0), 0)
        safe_ip = (client_ip or "unknown").strip() or "unknown"

        def _op() -> Tuple[bool, str, Dict]:
            conn = DatabaseFactory.get_connection()
            conn.isolation_level = None
            try:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT stock_count FROM analyze_global_daily WHERE usage_date = ?",
                    (today,),
                )
                row = cursor.fetchone()
                used_global = int(row["stock_count"]) if row else 0
                if used_global + len(codes) > global_max:
                    conn.execute("ROLLBACK")
                    logger.warning(
                        f"[AnalyzeSpend] global daily cap hit ip={safe_ip} user={user_id} "
                        f"used={used_global} need={len(codes)} cap={global_max}"
                    )
                    return False, "global_daily_exceeded", {
                        "message": "今日全站分析次数已达上限，请明天再试",
                        "remaining_quota": max(0, global_max - used_global),
                        "required_quota": len(codes),
                    }

                seen: List[str] = []
                new_codes: List[str] = []
                if enforce_ip_quota:
                    seen = self._seen_codes_with_cursor(cursor, today, safe_ip)
                    seen_set = set(seen)
                    new_codes = [code for code in codes if code not in seen_set]
                    remaining = max(0, ip_limit - len(seen))
                    if len(new_codes) > remaining:
                        conn.execute("ROLLBACK")
                        logger.warning(
                            f"[AnalyzeSpend] ip quota hit ip={safe_ip} user={user_id} "
                            f"used={len(seen)} need={len(new_codes)} cap={ip_limit}"
                        )
                        status = {
                            "total_quota": ip_limit,
                            "used_quota": len(seen),
                            "analyzed_stocks_today": seen,
                        }
                        return False, "quota_exceeded", {
                            "remaining_quota": remaining,
                            "required_quota": len(new_codes),
                            "new_codes": new_codes,
                            "total_quota": ip_limit,
                            "analyzed_stocks_today": seen,
                            "message": self._ip_quota_message(status),
                        }
                    for code in new_codes:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO analyze_ip_daily
                            (usage_date, client_ip, stock_code)
                            VALUES (?, ?, ?)
                            """,
                            (today, safe_ip, code),
                        )

                cursor.execute(
                    """
                    INSERT INTO analyze_global_daily (usage_date, stock_count)
                    VALUES (?, ?)
                    ON CONFLICT(usage_date) DO UPDATE SET
                        stock_count = stock_count + excluded.stock_count
                    """,
                    (today, len(codes)),
                )
                conn.execute("COMMIT")
                return True, "reserved", {
                    "required_quota": len(new_codes) if enforce_ip_quota else len(codes),
                    "global_used_after": used_global + len(codes),
                }
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
            finally:
                conn.close()

        try:
            return run_with_busy_retry(_op)
        except sqlite3.Error as exc:
            logger.error(f"[AnalyzeSpend] reserve failed closed: {exc}")
            raise SpendGuardUnavailable("analyze spend guard unavailable") from exc

    def _invite_quota(self, user_id: str) -> int:
        if not user_id:
            return 0
        try:
            status = QuotaService(db_path=self.db_path).get_quota_status(
                user_id,
                is_authenticated=False,
            )
            return max(int(status.get("invite_quota") or 0), 0)
        except Exception as exc:
            logger.warning(f"[AnalyzeSpend] invite quota lookup skipped: {exc}")
            return 0

    def _seen_codes(self, usage_date: str, client_ip: str) -> List[str]:
        with DatabaseFactory.get_connection() as conn:
            cursor = conn.cursor()
            return self._seen_codes_with_cursor(cursor, usage_date, client_ip)

    @staticmethod
    def _seen_codes_with_cursor(cursor, usage_date: str, client_ip: str) -> List[str]:
        cursor.execute(
            """
            SELECT stock_code FROM analyze_ip_daily
            WHERE usage_date = ? AND client_ip = ?
            ORDER BY created_at ASC, stock_code ASC
            """,
            (usage_date, client_ip),
        )
        return [row["stock_code"] for row in cursor.fetchall() or []]

    @staticmethod
    def _ip_quota_message(status: Dict) -> str:
        analyzed = status.get("analyzed_stocks_today") or []
        total = status.get("total_quota", 0)
        message = f"今日新股票分析次数已用完 ({total}/{total})\n\n"
        message += "💡 建议：\n"
        if analyzed:
            message += f"- 重新查看今日已分析的 {len(analyzed)} 支股票,深化判断\n"
        message += "- 绑定邮箱后，邀请奖励记在账户上\n"
        message += "- 明日额度将自动恢复\n\n"
        message += "💡 提示：同一网络下的未登录次数合并计算"
        return message
