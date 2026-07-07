-- Watchlist structure signal alerts
-- Notify users when a watchlist symbol triggers a structure signal
-- (MA crossover / MA20 breakout / volume spike) after market close.

CREATE TABLE IF NOT EXISTS watchlist_signal_alerts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    title TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read_at TEXT,
    UNIQUE(user_id, ts_code, trade_date, signal_type)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_signal_alerts_user
    ON watchlist_signal_alerts(user_id);

CREATE INDEX IF NOT EXISTS idx_watchlist_signal_alerts_unread
    ON watchlist_signal_alerts(user_id, read_at);
