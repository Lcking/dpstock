"""
Shared pytest fixtures for isolated database tests.
Prevents tests from writing sqlite WAL/SHM files into data/.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from database.db_factory import DatabaseFactory

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = REPO_ROOT / "migrations"

INTEGRATION_MIGRATIONS = [
    "004_create_watchlist_tables.sql",
    "006_recreate_judgments_table.sql",
    "008_create_user_tables.sql",
    "013_add_watchlist_item_weight.sql",
]


def apply_migrations(db_path: Path, migration_names: list[str]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for migration_name in migration_names:
            sql = (MIGRATIONS_DIR / migration_name).read_text(encoding="utf-8")
            conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def isolated_db(tmp_path):
    """Initialize DatabaseFactory against a temp sqlite file with core schema."""
    db_path = tmp_path / "test.db"
    apply_migrations(db_path, INTEGRATION_MIGRATIONS)
    DatabaseFactory.initialize(str(db_path))
    return db_path
