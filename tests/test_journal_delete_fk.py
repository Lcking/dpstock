"""判断日记删除：judgment_checks 的坏外键不得阻断 DELETE FROM judgments。

bug 现场：judgment_checks(001/judgment_service) 的外键指向 judgments(judgment_id)，
但 006 重建后 judgments 已无该列。连接层 PRAGMA foreign_keys=ON 后，
删除判断记录直接 500：foreign key mismatch。
"""
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = REPO_ROOT / "migrations"


def _exec_migration(conn: sqlite3.Connection, name: str) -> None:
    sql = (MIGRATIONS_DIR / name).read_text(encoding="utf-8")
    conn.executescript(sql)


def _make_prod_like_db(db_path: Path) -> None:
    """还原生产状态：006 版 judgments + 带坏外键的 judgment_checks。"""
    conn = sqlite3.connect(db_path)
    _exec_migration(conn, "006_recreate_judgments_table.sql")
    conn.executescript(
        """
        CREATE TABLE judgment_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judgment_id TEXT NOT NULL,
            check_time TIMESTAMP NOT NULL,
            current_price REAL,
            price_change_pct REAL,
            current_structure_status TEXT,
            status_description TEXT,
            reasons TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (judgment_id) REFERENCES judgments(judgment_id)
        );
        INSERT INTO judgment_checks (judgment_id, check_time, current_price)
        VALUES ('legacy-uuid', '2026-06-01T00:00:00', 7.5);
        """
    )
    conn.execute(
        "INSERT INTO judgments (id, user_id, stock_code, candidate, status, created_at, updated_at) "
        "VALUES ('jr_dup2', 'user_1', '002129.SZ', 'B', 'active', 't', 't')"
    )
    conn.commit()
    conn.close()


def test_bad_fk_blocks_delete_then_migration_018_fixes_it(tmp_path):
    db_path = tmp_path / "prod_like.db"
    _make_prod_like_db(db_path)

    # 复现：foreign_keys=ON 时删除报 mismatch
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(sqlite3.OperationalError, match="foreign key mismatch"):
        conn.execute("DELETE FROM judgments WHERE id='jr_dup2' AND user_id='user_1'")
    conn.close()

    # 应用 018 修复
    conn = sqlite3.connect(db_path)
    _exec_migration(conn, "018_fix_judgment_checks_fk.sql")
    conn.commit()

    # 数据保留
    kept = conn.execute("SELECT COUNT(*) FROM judgment_checks").fetchone()[0]
    assert kept == 1

    # 删除恢复正常
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.execute("DELETE FROM judgments WHERE id='jr_dup2' AND user_id='user_1'")
    assert cur.rowcount == 1
    conn.close()


def test_full_migration_stack_allows_journal_delete(tmp_path, monkeypatch):
    """全量迁移 + JudgmentService 初始化后，删除判断记录必须可用。"""
    import os

    db_path = tmp_path / "full.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    original_cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        from scripts.run_migrations import run_migrations

        run_migrations()
    finally:
        os.chdir(original_cwd)

    from database.db_factory import DatabaseFactory
    from services.judgment_service import JudgmentService
    from services.journal.service import JournalService

    DatabaseFactory.initialize(str(db_path))
    JudgmentService(db_path=str(db_path))  # _init_db 不得重建坏外键

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    # judgment_checks 不应再有指向 judgments(judgment_id) 的外键
    fk_rows = conn.execute("PRAGMA foreign_key_list(judgment_checks)").fetchall()
    assert fk_rows == []
    conn.execute(
        "INSERT INTO judgments (id, user_id, stock_code, candidate, status, created_at, updated_at) "
        "VALUES ('jr_del_ok', 'user_9', '002129.SZ', 'B', 'active', 't', 't')"
    )
    conn.commit()
    conn.close()

    service = JournalService()
    assert service.delete_record(record_id="jr_del_ok", user_id="user_9") is True
