#!/usr/bin/env python3
"""
Run all SQL migrations in valid order
"""
import sqlite3
import os
import sys
from datetime import datetime


def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _count_rows(cursor: sqlite3.Cursor, table_name: str) -> int:
    if not _table_exists(cursor, table_name):
        return 0
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _ensure_migrations_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )


def _load_applied(cursor: sqlite3.Cursor) -> set:
    _ensure_migrations_table(cursor)
    cursor.execute("SELECT name FROM schema_migrations")
    return {r[0] for r in cursor.fetchall()}


def _mark_applied(cursor: sqlite3.Cursor, name: str) -> None:
    cursor.execute(
        "INSERT OR IGNORE INTO schema_migrations(name, applied_at) VALUES (?, ?)",
        (name, datetime.utcnow().isoformat() + "Z"),
    )

def run_migrations():
    db_path = os.getenv("DB_PATH") or 'data/stocks.db'
    migrations_dir = 'migrations'
    
    print(f"Applying migrations to {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    _ensure_migrations_table(cursor)
    conn.commit()
    
    # Get all .sql files sorted
    files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
    applied = _load_applied(cursor)
    
    for f in files:
        file_path = os.path.join(migrations_dir, f)
        if f in applied:
            print(f"  Skipping {f}... already applied")
            continue

        print(f"  Running {f}...", end=" ")
        
        try:
            with open(file_path, 'r') as sql_file:
                sql_script = sql_file.read()
                # Safety: avoid destructive migration that drops judgments when data exists
                if (
                    f.startswith("006_")
                    and ("DROP TABLE IF EXISTS judgments" in sql_script or "DROP TABLE IF EXISTS judgment_checks" in sql_script)
                    and _count_rows(cursor, "judgments") > 0
                ):
                    print("SKIPPED (dangerous: judgments not empty)")
                    _mark_applied(cursor, f)
                    conn.commit()
                    applied.add(f)
                    continue

                cursor.executescript(sql_script)

            _mark_applied(cursor, f)
            conn.commit()
            applied.add(f)
            print("OK")
        except Exception as e:
            msg = str(e)
            print(f"FAILED: {msg}")

            # Some migrations are legacy and may fail harmlessly on newer schemas.
            # If we keep retrying them on every startup, it creates noise and may cause unintended side effects.
            harmless_markers = (
                "duplicate column name",
                "already exists",
                "no such column: judgment_id",
                "no such table",
            )
            if any(m in msg.lower() for m in harmless_markers):
                print(f"  -> Marking {f} as applied (harmless failure)")
                _mark_applied(cursor, f)
                conn.commit()
                applied.add(f)
                continue

            # For unknown errors, stop to avoid partial / corrupt schema changes.
            conn.rollback()
            conn.close()
            raise
            
    conn.close()
    print("✓ All migrations completed.")

if __name__ == "__main__":
    if not os.path.exists('data'):
        os.makedirs('data')
    run_migrations()
