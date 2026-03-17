import os
import sqlite3
from pathlib import Path

from database.db_factory import DatabaseFactory
from scripts.run_migrations import run_migrations
from services.invite_service import InviteService
from services.quota_service import QuotaService
from services.user_service import UserService


def _apply_migration(db_path: Path, migration_name: str) -> None:
    migration_path = Path(__file__).resolve().parents[1] / "migrations" / migration_name
    sql = migration_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def _run_all_migrations(db_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    original_cwd = Path.cwd()
    original_db_path = os.environ.get("DB_PATH")

    os.environ["DB_PATH"] = str(db_path)
    os.chdir(repo_root)
    try:
        run_migrations()
    finally:
        os.chdir(original_cwd)
        if original_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = original_db_path


def test_create_user_from_email_binding(tmp_path):
    db_path = tmp_path / "users.db"
    _apply_migration(db_path, "008_create_user_tables.sql")
    DatabaseFactory.initialize(str(db_path))

    service = UserService(db_path=str(db_path))
    user_id = service.get_or_create_user_by_identity(
        identity_type="email_anchor",
        identity_value="anchor_xxx",
    )

    user = service.get_user(user_id)
    assert user is not None
    assert user["user_id"] == user_id
    assert user["status"] == "active"
    assert user["email_verified"] == 0


def test_resolve_existing_identity_returns_same_user(tmp_path):
    db_path = tmp_path / "users.db"
    _apply_migration(db_path, "008_create_user_tables.sql")
    DatabaseFactory.initialize(str(db_path))

    service = UserService(db_path=str(db_path))
    first_user_id = service.get_or_create_user_by_identity(
        identity_type="anonymous",
        identity_value="anon_123",
    )

    second_user_id = service.get_or_create_user_by_identity(
        identity_type="anonymous",
        identity_value="anon_123",
    )

    assert second_user_id == first_user_id
    assert service.resolve_identity("anonymous", "anon_123") == first_user_id


def test_full_migration_stack_creates_unified_user_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "users.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    _run_all_migrations(db_path)

    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()

    assert "users" in tables
    assert "user_identities" in tables


def test_bind_email_merges_anonymous_cookie_and_anchor_to_same_user(tmp_path):
    db_path = tmp_path / "users.db"
    _run_all_migrations(db_path)
    DatabaseFactory.initialize(str(db_path))

    service = UserService(db_path=str(db_path))

    service.get_or_create_user_by_identity(
        identity_type="anonymous",
        identity_value="anon_1",
    )
    service.get_or_create_user_by_identity(
        identity_type="cookie_uid",
        identity_value="cookie_1",
    )
    service.get_or_create_user_by_identity(
        identity_type="email_anchor",
        identity_value="anchor_1",
    )

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO watchlists (id, user_id, name, created_at, updated_at)
            VALUES ('wl_test', 'cookie_1', '临时观察', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_records (user_id, stock_code, analysis_date)
            VALUES ('anon_1', '600519.SH', '2026-01-01')
            """
        )
        conn.execute(
            """
            INSERT INTO invite_codes (invite_code, inviter_id)
            VALUES ('invite001', 'cookie_1')
            """
        )
        conn.commit()
    finally:
        conn.close()

    user_id = service.bind_email_identity(
        anonymous_id="anon_1",
        cookie_uid="cookie_1",
        anchor_id="anchor_1",
        email="test@example.com",
    )

    assert service.resolve_identity("anonymous", "anon_1") == user_id
    assert service.resolve_identity("cookie_uid", "cookie_1") == user_id
    assert service.resolve_identity("email_anchor", "anchor_1") == user_id

    user = service.get_user(user_id)
    assert user is not None
    assert user["primary_email"] == "test@example.com"
    assert user["email_verified"] == 1

    conn = sqlite3.connect(db_path)
    try:
        watchlist_owner = conn.execute(
            "SELECT user_id FROM watchlists WHERE id = 'wl_test'"
        ).fetchone()[0]
        analysis_owner = conn.execute(
            "SELECT user_id FROM analysis_records WHERE stock_code = '600519.SH'"
        ).fetchone()[0]
        invite_owner = conn.execute(
            "SELECT inviter_id FROM invite_codes WHERE invite_code = 'invite001'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert watchlist_owner == user_id
    assert analysis_owner == user_id
    assert invite_owner == user_id


def test_resolve_request_user_prefers_bound_unified_user(tmp_path):
    db_path = tmp_path / "users.db"
    _run_all_migrations(db_path)
    DatabaseFactory.initialize(str(db_path))

    service = UserService(db_path=str(db_path))
    bound_user_id = service.bind_email_identity(
        anonymous_id="anon_2",
        cookie_uid="cookie_2",
        anchor_id="anchor_2",
        email="bound@example.com",
    )

    assert service.resolve_request_user(cookie_uid="cookie_2")["user_id"] == bound_user_id
    assert service.resolve_request_user(anonymous_id="anon_2")["user_id"] == bound_user_id
    assert service.resolve_request_user(anchor_id="anchor_2")["user_id"] == bound_user_id


def test_invite_reward_uses_canonical_user_after_inviter_binding(tmp_path):
    db_path = tmp_path / "users.db"
    _run_all_migrations(db_path)
    DatabaseFactory.initialize(str(db_path))

    user_service = UserService(db_path=str(db_path))
    invite_service = InviteService(db_path=str(db_path))
    quota_service = QuotaService(db_path=str(db_path))

    legacy_inviter_id = "cookie_inviter"
    invitee_anon_id = "anon_invitee"

    user_service.get_or_create_user_by_identity(
        identity_type="cookie_uid",
        identity_value=legacy_inviter_id,
    )
    invitee_user_id = user_service.get_or_create_user_by_identity(
        identity_type="anonymous",
        identity_value=invitee_anon_id,
    )

    generated = invite_service.generate_invite_code(legacy_inviter_id)
    assert generated["invite_code"]

    canonical_inviter_id = user_service.bind_email_identity(
        cookie_uid=legacy_inviter_id,
        anchor_id="anchor_inviter",
        email="inviter@example.com",
    )

    quota_service.record_analysis(invitee_user_id, "600519.SH")
    reward = invite_service.check_and_reward_inviter(
        invitee_id=invitee_user_id,
        referrer_id=legacy_inviter_id,
    )

    assert reward is not None
    assert reward["inviter_id"] == canonical_inviter_id

    quota_status = quota_service.get_quota_status(canonical_inviter_id)
    assert quota_status["invite_quota"] == InviteService.REWARD_QUOTA

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT inviter_id, invitee_id FROM invite_rewards"
        ).fetchall()
    finally:
        conn.close()

    assert rows == [(canonical_inviter_id, invitee_user_id)]
