-- Migration 015: Ops observability tables (N7)

CREATE TABLE IF NOT EXISTS job_health (
    job_id TEXT PRIMARY KEY,
    last_run_at TEXT,
    last_success_at TEXT,
    last_status TEXT NOT NULL DEFAULT 'unknown',
    last_error TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_usage_daily (
    usage_date DATE NOT NULL,
    user_type TEXT NOT NULL,
    call_count INTEGER NOT NULL DEFAULT 0,
    stock_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (usage_date, user_type)
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_daily_date
    ON llm_usage_daily(usage_date DESC);
