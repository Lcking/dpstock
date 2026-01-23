-- Migration 004: Watchlist Tables
-- 自选股列表表结构

-- 自选股列表
CREATE TABLE IF NOT EXISTS watchlists (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '默认自选',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 自选股列表项目
CREATE TABLE IF NOT EXISTS watchlist_items (
    watchlist_id TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    name TEXT,  -- 股票名称缓存
    added_at TEXT NOT NULL,
    PRIMARY KEY (watchlist_id, ts_code),
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_items_code ON watchlist_items(ts_code);
