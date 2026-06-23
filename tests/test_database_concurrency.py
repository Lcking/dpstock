import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from database.db_factory import DatabaseFactory

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = REPO_ROOT / "migrations"


def apply_migrations(db_path: Path, migration_names: list[str]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for migration_name in migration_names:
            sql = (MIGRATIONS_DIR / migration_name).read_text(encoding="utf-8")
            conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def test_database_factory_sets_busy_timeout_and_wal(tmp_path, monkeypatch):
    db_path = tmp_path / "pragma.db"
    monkeypatch.setenv("DB_ENABLE_WAL", "true")
    monkeypatch.setenv("DB_TIMEOUT", "15")
    DatabaseFactory.initialize(str(db_path))

    with DatabaseFactory.get_connection() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()["journal_mode"]
        busy_timeout = int(list(conn.execute("PRAGMA busy_timeout").fetchone().values())[0])

    assert journal_mode.lower() == "wal"
    assert int(busy_timeout) == 15000


def test_concurrent_analysis_record_writes_do_not_lock(tmp_path):
    db_path = tmp_path / "concurrency.db"
    apply_migrations(db_path, ["002_create_quota_tables.sql"])
    DatabaseFactory.initialize(str(db_path))

    def write_row(index: int) -> None:
        with DatabaseFactory.get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO analysis_records (user_id, stock_code, analysis_date)
                VALUES (?, ?, date('now'))
                """,
                (f"user_{index % 3}", f"{600000 + index}.SH"),
            )
            conn.commit()

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(write_row, range(40)))

    assert results == [None] * 40
    with DatabaseFactory.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM analysis_records").fetchone()["c"]
    assert count == 40
