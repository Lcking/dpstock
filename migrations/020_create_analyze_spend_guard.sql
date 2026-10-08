-- Persist analyze spend limits so a restart cannot reset them.

CREATE TABLE IF NOT EXISTS analyze_global_daily (
    usage_date TEXT PRIMARY KEY,
    stock_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS analyze_ip_daily (
    usage_date TEXT NOT NULL,
    client_ip TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usage_date, client_ip, stock_code)
);

CREATE INDEX IF NOT EXISTS idx_analyze_ip_daily_ip
    ON analyze_ip_daily(usage_date, client_ip);
