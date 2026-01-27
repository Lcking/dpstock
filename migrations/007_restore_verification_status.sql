-- Migration 007: Restore Verification Status Columns
-- 修复 Migration 006 意外移除的验证字段
-- 添加 verification_result 以存储详细验证数据

-- 1. 添加 verification_status (PENDING/CONFIRMED/FALSIFIED/UNCERTAIN)
ALTER TABLE judgments ADD COLUMN verification_status TEXT DEFAULT 'PENDING';

-- 2. 添加 verification_result (JSON)
ALTER TABLE judgments ADD COLUMN verification_result TEXT;

-- 3. 创建索引
CREATE INDEX IF NOT EXISTS idx_judgments_ver_status ON judgments(verification_status);
