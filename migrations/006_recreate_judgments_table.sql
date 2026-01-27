-- Migration 006: Recreate Judgments Table
-- 完全重构 judgments 表以匹配 JournalService (v0.2)
-- 之前的 001 和 005 定义混乱，此迁移将标准化表结构

DROP TABLE IF EXISTS judgment_checks;
DROP TABLE IF EXISTS judgments;

-- Table: judgments
-- Stores user judgment records and snapshots
CREATE TABLE judgments (
    id TEXT PRIMARY KEY,          -- UUID (e.g. "jr_...")
    user_id TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    candidate TEXT,               -- A/B/C
    selected_premises TEXT,       -- JSON array
    selected_risk_checks TEXT,    -- JSON array
    constraints TEXT,             -- JSON object
    snapshot TEXT,                -- JSON object
    validation_date TEXT,         -- ISO8601 Timestamp
    status TEXT DEFAULT 'active', -- active/due/reviewed/archived
    review TEXT,                  -- JSON object
    created_at TEXT NOT NULL,     -- ISO8601 Timestamp
    updated_at TEXT NOT NULL      -- ISO8601 Timestamp
);

-- Indexes
CREATE INDEX idx_judgments_user_id ON judgments(user_id);
CREATE INDEX idx_judgments_stock_code ON judgments(stock_code);
CREATE INDEX idx_judgments_status ON judgments(status);
CREATE INDEX idx_judgments_validation ON judgments(validation_date);
CREATE INDEX idx_judgments_created_at ON judgments(created_at DESC);
