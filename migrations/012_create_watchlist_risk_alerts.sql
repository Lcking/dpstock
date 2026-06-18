-- Watchlist risk alerts
-- Notify users when a watchlist symbol appears in the daily risk stock list.

CREATE TABLE IF NOT EXISTS watchlist_risk_alerts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read_at TEXT,
    UNIQUE(user_id, ts_code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_risk_alerts_user
    ON watchlist_risk_alerts(user_id);

CREATE INDEX IF NOT EXISTS idx_watchlist_risk_alerts_unread
    ON watchlist_risk_alerts(user_id, read_at);
