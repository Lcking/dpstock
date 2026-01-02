-- Quota & Invite System Database Migration
-- Version: 002
-- Description: Create tables for analysis quota tracking and invite rewards

-- ============================================
-- Table 1: Analysis Records
-- Purpose: Track each analysis to determine quota consumption
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,                    -- aguai_uid from cookie
    stock_code TEXT NOT NULL,                 -- Stock code (e.g., "000001")
    analysis_date DATE NOT NULL,              -- Analysis date (YYYY-MM-DD)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent duplicate records for same user+stock+date
    UNIQUE(user_id, stock_code, analysis_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_analysis_user_date 
    ON analysis_records(user_id, analysis_date);

CREATE INDEX IF NOT EXISTS idx_analysis_stock 
    ON analysis_records(stock_code);


-- ============================================
-- Table 2: Invite Codes
-- Purpose: Store generated invite codes
-- ============================================
CREATE TABLE IF NOT EXISTS invite_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invite_code TEXT UNIQUE NOT NULL,         -- Unique invite code (8 chars)
    inviter_id TEXT NOT NULL,                 -- Inviter's aguai_uid
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP                      -- Optional expiration (NULL = never expires)
);

-- Index for inviter lookup
CREATE INDEX IF NOT EXISTS idx_invite_inviter 
    ON invite_codes(inviter_id);


-- ============================================
-- Table 3: Invite Rewards
-- Purpose: Track invite rewards to prevent duplicates and calculate daily quota
-- ============================================
CREATE TABLE IF NOT EXISTS invite_rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inviter_id TEXT NOT NULL,                 -- Inviter's aguai_uid
    invitee_id TEXT NOT NULL,                 -- Invitee's aguai_uid
    invite_code TEXT NOT NULL,                -- Invite code used
    reward_quota INTEGER DEFAULT 5,           -- Reward amount (default 5)
    reward_date DATE NOT NULL,                -- Date reward was granted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent same invitee from rewarding inviter multiple times
    UNIQUE(inviter_id, invitee_id)
);

-- Indexes for reward calculation
CREATE INDEX IF NOT EXISTS idx_reward_inviter_date 
    ON invite_rewards(inviter_id, reward_date);

CREATE INDEX IF NOT EXISTS idx_reward_invitee 
    ON invite_rewards(invitee_id);
