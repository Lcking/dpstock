-- Migration 003: Create Anchor Tables for Email Binding System
-- Purpose: Enable anonymous users to bind email for cross-device judgment recovery
-- Date: 2026-01-15

-- 1. Create anchors table (email binding credentials)
CREATE TABLE IF NOT EXISTS anchors (
    anchor_id TEXT PRIMARY KEY,              -- UUID
    anchor_type TEXT NOT NULL DEFAULT 'email', -- Fixed to 'email' for V-1
    anchor_value_hash TEXT UNIQUE NOT NULL,  -- SHA256(email) for lookup
    anchor_value_masked TEXT,                -- Masked email like u***@example.com
    created_at TEXT NOT NULL                 -- ISO datetime
);

CREATE INDEX IF NOT EXISTS idx_anchors_hash ON anchors(anchor_value_hash);
CREATE INDEX IF NOT EXISTS idx_anchors_created ON anchors(created_at);

-- 2. Create email_codes table (verification codes)
CREATE TABLE IF NOT EXISTS email_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_hash TEXT NOT NULL,                -- SHA256(email)
    code TEXT NOT NULL,                      -- 6-digit verification code
    expires_at TEXT NOT NULL,                -- ISO datetime (10 minutes from creation)
    created_at TEXT NOT NULL,                -- ISO datetime
    send_count INTEGER DEFAULT 1,            -- Rate limiting counter
    used INTEGER DEFAULT 0                   -- 0=unused, 1=used (prevent reuse)
);

CREATE INDEX IF NOT EXISTS idx_email_codes_hash ON email_codes(email_hash);
CREATE INDEX IF NOT EXISTS idx_email_codes_expires ON email_codes(expires_at);
CREATE INDEX IF NOT EXISTS idx_email_codes_created ON email_codes(created_at);

-- 3. Alter judgments table to support owner system
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
-- We'll use a safer approach: try to add columns and ignore errors

-- Add owner_type column (default 'anonymous')
-- If column exists, this will fail silently
PRAGMA foreign_keys=off;

-- Create a backup table with new schema
CREATE TABLE IF NOT EXISTS judgments_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    judgment_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    owner_type TEXT DEFAULT 'anonymous',
    owner_id TEXT,
    stock_code TEXT NOT NULL,
    stock_name TEXT,
    market_type TEXT,
    snapshot_time TIMESTAMP NOT NULL,
    structure_premise TEXT,
    selected_candidates TEXT,
    key_levels_snapshot TEXT,
    structure_type TEXT,
    ma200_position TEXT,
    phase TEXT,
    verification_period INTEGER DEFAULT 7,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Copy existing data
INSERT OR IGNORE INTO judgments_new 
SELECT 
    id, judgment_id, user_id,
    'anonymous' as owner_type,
    user_id as owner_id,
    stock_code, stock_name, market_type,
    snapshot_time, structure_premise, selected_candidates,
    key_levels_snapshot, structure_type, ma200_position, phase,
    verification_period,
    created_at,
    datetime('now') as updated_at
FROM judgments;

-- Drop old table and rename new one
DROP TABLE judgments;
ALTER TABLE judgments_new RENAME TO judgments;

-- Create index for owner-based queries
CREATE INDEX IF NOT EXISTS idx_judgments_owner ON judgments(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_judgments_created ON judgments(created_at);

-- 4. Migrate existing data
-- Set owner_type and owner_id for existing judgments
-- Assuming existing judgments use 'user_id' field as anonymous_id
UPDATE judgments 
SET owner_type = 'anonymous',
    owner_id = COALESCE(user_id, 'legacy-' || id),
    created_at = COALESCE(created_at, datetime('now')),
    updated_at = datetime('now')
WHERE owner_id IS NULL;

-- 5. Create anchor_tokens table (optional, for token management)
-- If using database-stored tokens instead of JWT
CREATE TABLE IF NOT EXISTS anchor_tokens (
    token TEXT PRIMARY KEY,
    anchor_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (anchor_id) REFERENCES anchors(anchor_id)
);

CREATE INDEX IF NOT EXISTS idx_anchor_tokens_anchor ON anchor_tokens(anchor_id);
CREATE INDEX IF NOT EXISTS idx_anchor_tokens_expires ON anchor_tokens(expires_at);

-- Migration complete
-- Next steps:
-- 1. Implement anchor_service.py
-- 2. Create API routes in routes/anchor.py
-- 3. Update judgment routes to use owner system
