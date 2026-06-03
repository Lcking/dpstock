import pytest

from database.db_factory import DatabaseFactory
from routes.admin import admin_invite_summary
from scripts.run_migrations import run_migrations


def _run_all_migrations(db_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(db_path))
    run_migrations()


@pytest.mark.asyncio
async def test_admin_invite_summary_reports_funnel_counts(tmp_path, monkeypatch):
    db_path = tmp_path / "admin_invite_funnel.db"
    _run_all_migrations(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    with DatabaseFactory.get_connection() as conn:
        conn.execute(
            "INSERT INTO invite_codes (invite_code, inviter_id) VALUES (?, ?)",
            ("code001", "inviter_1"),
        )
        conn.execute(
            """
            INSERT INTO invite_acceptances (inviter_id, invitee_id, invite_code)
            VALUES (?, ?, ?)
            """,
            ("inviter_1", "invitee_1", "code001"),
        )
        conn.execute(
            """
            INSERT INTO invite_rewards (inviter_id, invitee_id, invite_code, reward_quota, reward_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("inviter_1", "invitee_1", "code001", 5, "2026-06-03"),
        )
        conn.commit()

    summary = await admin_invite_summary({})

    assert summary["invite_codes_total"] == 1
    assert summary["invite_acceptances_total"] == 1
    assert summary["invite_rewards_total"] == 1
    assert summary["acceptance_rate"] == 100.0
    assert summary["reward_rate"] == 100.0
