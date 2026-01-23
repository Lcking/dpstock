-- Migration 005: Add Journal fields to judgments table
-- 为 judgments 表添加 Journal 模块需要的字段

-- 添加 candidate 字段 (A/B/C)
ALTER TABLE judgments ADD COLUMN candidate TEXT;

-- 添加 selected_premises (JSON array)
ALTER TABLE judgments ADD COLUMN selected_premises TEXT;

-- 添加 selected_risk_checks (JSON array)
ALTER TABLE judgments ADD COLUMN selected_risk_checks TEXT;

-- 添加 constraints (JSON object - DecisionConstraints)
ALTER TABLE judgments ADD COLUMN constraints TEXT;

-- 添加 snapshot (JSON object - 创建时的快照)
ALTER TABLE judgments ADD COLUMN snapshot TEXT;

-- 添加 validation_date (验证到期日)
ALTER TABLE judgments ADD COLUMN validation_date TEXT;

-- 添加 status (active/due/reviewed/archived)
ALTER TABLE judgments ADD COLUMN status TEXT DEFAULT 'active';

-- 添加 review (JSON object - 复盘结果)
ALTER TABLE judgments ADD COLUMN review TEXT;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_judgments_status ON judgments(status);
CREATE INDEX IF NOT EXISTS idx_judgments_validation ON judgments(validation_date);
