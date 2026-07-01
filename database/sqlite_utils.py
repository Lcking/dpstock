"""
Shared SQLite PRAGMA configuration for all app connections.
"""
from __future__ import annotations

import sqlite3

from config.database import DatabaseConfig


def configure_sqlite_connection(conn: sqlite3.Connection) -> None:
    busy_timeout_ms = max(int(DatabaseConfig.timeout() * 1000), 1000)
    conn.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
    if DatabaseConfig.enable_wal():
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
