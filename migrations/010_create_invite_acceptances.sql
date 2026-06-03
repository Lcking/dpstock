-- Invite acceptance funnel
-- Records users who opened a valid invite link before they complete first analysis.

CREATE TABLE IF NOT EXISTS invite_acceptances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inviter_id TEXT NOT NULL,
    invitee_id TEXT NOT NULL,
    invite_code TEXT NOT NULL,
    accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- One user can only be attributed to one inviter.
    UNIQUE(invitee_id)
);

CREATE INDEX IF NOT EXISTS idx_invite_acceptances_inviter
    ON invite_acceptances(inviter_id);

CREATE INDEX IF NOT EXISTS idx_invite_acceptances_code
    ON invite_acceptances(invite_code);
