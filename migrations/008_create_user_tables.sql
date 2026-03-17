-- Migration 008: Create unified user identity tables
-- Purpose: Introduce a stable user_id and identity mapping layer without
--          breaking existing anonymous / anchor based flows.

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    primary_email TEXT,
    email_verified INTEGER NOT NULL DEFAULT 0,
    display_name TEXT,
    profile_completed INTEGER NOT NULL DEFAULT 0,
    is_public_analysis_enabled INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    last_active_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_primary_email ON users(primary_email);

CREATE TABLE IF NOT EXISTS user_identities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identity_type TEXT NOT NULL,
    identity_value TEXT NOT NULL,
    user_id TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    verified_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_identities_unique_identity
ON user_identities(identity_type, identity_value);

CREATE INDEX IF NOT EXISTS idx_user_identities_user_id
ON user_identities(user_id);

CREATE INDEX IF NOT EXISTS idx_user_identities_type
ON user_identities(identity_type);
