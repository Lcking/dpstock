-- Migration: Add verification status fields to judgments table
-- Purpose: Enable judgment verification system V1
-- Date: 2026-01-18

-- Add verification status fields
ALTER TABLE judgments ADD COLUMN verification_status TEXT DEFAULT 'WAITING';
ALTER TABLE judgments ADD COLUMN last_checked_at TEXT;
ALTER TABLE judgments ADD COLUMN verification_reason TEXT;

-- Update verification_period default to 1 day (for short-term traders)
-- Note: This only affects new records, existing records keep their values
-- We'll handle existing records separately if needed

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_judgments_verification_status 
ON judgments(verification_status);

CREATE INDEX IF NOT EXISTS idx_judgments_last_checked 
ON judgments(last_checked_at);

-- Add owner_type and owner_id indexes if not exist (for verification queries)
CREATE INDEX IF NOT EXISTS idx_judgments_owner 
ON judgments(owner_type, owner_id);
