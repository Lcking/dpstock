"""
Shared SQLite PRAGMA configuration for all app connections.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Callable, TypeVar

from config.database import DatabaseConfig

T = TypeVar("T")


def configure_sqlite_connection(conn: sqlite3.Connection) -> None:
    busy_timeout_ms = max(int(DatabaseConfig.timeout() * 1000), 1000)
    conn.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
    if DatabaseConfig.enable_wal():
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")


def run_with_busy_retry(
    operation: Callable[[], T],
    *,
    max_attempts: int = 8,
    base_delay_s: float = 0.01,
) -> T:
    """Retry SQLite writes when another connection briefly holds the database lock."""
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(max_attempts):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "locked" not in message and "busy" not in message:
                raise
            last_error = exc
            if attempt == max_attempts - 1:
                raise
            time.sleep(base_delay_s * (2 ** attempt))
    if last_error is not None:
        raise last_error
    raise RuntimeError("run_with_busy_retry exited without result")
