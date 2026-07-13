-- Migration 018: 重建 judgment_checks，去掉指向已不存在列的外键
--
-- 历史问题：judgment_checks (001) 的外键是
--   FOREIGN KEY (judgment_id) REFERENCES judgments(judgment_id)
-- 但 006 重建 judgments 后已无 judgment_id 列。
-- 自从连接层开启 PRAGMA foreign_keys=ON 后，任何 DELETE FROM judgments
-- 都会触发 SQLite 外键校验并报错：
--   foreign key mismatch - "judgment_checks" referencing "judgments"
-- 表现为判断日记删除接口 500。

-- 若表不存在（全新库），先建一个占位，保证下方重建流程统一
CREATE TABLE IF NOT EXISTS judgment_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    judgment_id TEXT NOT NULL,
    check_time TIMESTAMP NOT NULL,
    current_price REAL,
    price_change_pct REAL,
    current_structure_status TEXT,
    status_description TEXT,
    reasons TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE judgment_checks RENAME TO judgment_checks_legacy_fk;

CREATE TABLE judgment_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    judgment_id TEXT NOT NULL,
    check_time TIMESTAMP NOT NULL,
    current_price REAL,
    price_change_pct REAL,
    current_structure_status TEXT,
    status_description TEXT,
    reasons TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO judgment_checks (
    id, judgment_id, check_time, current_price, price_change_pct,
    current_structure_status, status_description, reasons, created_at
)
SELECT
    id, judgment_id, check_time, current_price, price_change_pct,
    current_structure_status, status_description, reasons, created_at
FROM judgment_checks_legacy_fk;

DROP TABLE judgment_checks_legacy_fk;

CREATE INDEX IF NOT EXISTS idx_checks_judgment_id ON judgment_checks(judgment_id);
CREATE INDEX IF NOT EXISTS idx_checks_created_at ON judgment_checks(created_at DESC);
