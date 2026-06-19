-- Migration 013: optional position weight per watchlist symbol (percent, 0-100)
ALTER TABLE watchlist_items ADD COLUMN weight_pct REAL;
