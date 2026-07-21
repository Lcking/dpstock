-- Migration 019: 风险股池扩展字段
-- 支持：连续跌停天数、当日涨跌幅（5%/9% 涨幅池、创业板大波动池展示用）

ALTER TABLE risk_stock_items ADD COLUMN limit_down_days INTEGER DEFAULT 0;
ALTER TABLE risk_stock_items ADD COLUMN pct_chg REAL;
