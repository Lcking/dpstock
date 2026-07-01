-- Journal due-review digest email delivery log.

CREATE TABLE IF NOT EXISTS journal_due_email_log (
    user_id TEXT NOT NULL,
    digest_date TEXT NOT NULL,
    email TEXT NOT NULL,
    item_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'sent',
    error_message TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, digest_date)
);

CREATE INDEX IF NOT EXISTS idx_journal_due_email_log_digest_date
    ON journal_due_email_log(digest_date);
