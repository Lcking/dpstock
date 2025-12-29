-- Judgment API v0.1 Database Migration
-- Run this SQL to create the necessary tables

-- Table: judgments
-- Stores user judgment snapshots
CREATE TABLE IF NOT EXISTS judgments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    judgment_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT,
    market_type TEXT,
    snapshot_time TIMESTAMP NOT NULL,
    structure_premise TEXT,  -- JSON
    selected_candidates TEXT,  -- JSON array
    key_levels_snapshot TEXT,  -- JSON array
    structure_type TEXT,
    ma200_position TEXT,
    phase TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster user queries
CREATE INDEX IF NOT EXISTS idx_judgments_user_id ON judgments(user_id);
CREATE INDEX IF NOT EXISTS idx_judgments_stock_code ON judgments(stock_code);
CREATE INDEX IF NOT EXISTS idx_judgments_created_at ON judgments(created_at DESC);

-- Table: judgment_checks
-- Stores verification results for judgments
CREATE TABLE IF NOT EXISTS judgment_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    judgment_id TEXT NOT NULL,
    check_time TIMESTAMP NOT NULL,
    current_price REAL,
    price_change_pct REAL,
    current_structure_status TEXT,
    status_description TEXT,
    reasons TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (judgment_id) REFERENCES judgments(judgment_id)
);

-- Index for faster judgment detail queries
CREATE INDEX IF NOT EXISTS idx_checks_judgment_id ON judgment_checks(judgment_id);
CREATE INDEX IF NOT EXISTS idx_checks_created_at ON judgment_checks(created_at DESC);
