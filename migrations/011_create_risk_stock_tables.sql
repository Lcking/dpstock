-- Risk stock list
-- Tracks daily risk labels such as ST and 3+ consecutive limit-up stocks.

CREATE TABLE IF NOT EXISTS risk_stock_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    name TEXT NOT NULL,
    market TEXT,
    tags_json TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    reason TEXT NOT NULL,
    limit_up_days INTEGER DEFAULT 0,
    is_st INTEGER DEFAULT 0,
    source TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trade_date, ts_code)
);

CREATE INDEX IF NOT EXISTS idx_risk_stock_items_date
    ON risk_stock_items(trade_date);

CREATE INDEX IF NOT EXISTS idx_risk_stock_items_code
    ON risk_stock_items(ts_code);
