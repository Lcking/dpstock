-- User notification preferences and risk alert email delivery log.

ALTER TABLE users ADD COLUMN notify_pref TEXT DEFAULT '{"risk_alert_email":true}';

CREATE TABLE IF NOT EXISTS risk_alert_email_log (
    user_id TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    email TEXT NOT NULL,
    item_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'sent',
    error_message TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_risk_alert_email_log_trade_date
    ON risk_alert_email_log(trade_date);
