-- Admin: runtime app settings (non-secret keys; API_KEY remains env-only)
-- Nav: configurable header links

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_app_settings_updated ON app_settings(updated_at);

CREATE TABLE IF NOT EXISTS nav_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    href TEXT NOT NULL,
    target TEXT NOT NULL DEFAULT '_blank',
    rel TEXT NOT NULL DEFAULT 'noopener',
    sort_order INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nav_links_sort ON nav_links(sort_order, enabled);

INSERT INTO nav_links (label, href, target, rel, sort_order, enabled, created_at, updated_at)
SELECT '实盘策略平台', 'https://www.qifuapp.net/', '_blank', 'noopener sponsored', 0, 1, datetime('now'), datetime('now')
WHERE NOT EXISTS (SELECT 1 FROM nav_links LIMIT 1);
