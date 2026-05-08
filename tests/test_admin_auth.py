"""Admin auth helpers (no web_server import — avoids DB/app singleton)."""
import os

import pytest


def test_verify_admin_password_plain(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("ADMIN_PASSWORD", "secret123")
    from auth import admin_auth

    assert admin_auth.verify_admin_password("secret123") is True
    assert admin_auth.verify_admin_password("wrong") is False


def test_admin_login_configured(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    from auth import admin_auth

    assert admin_auth.admin_login_configured() is False

    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "x")
    assert admin_auth.admin_login_configured() is True


@pytest.mark.skipif(
    not os.getenv("RUN_ADMIN_BCRYPT_TEST"),
    reason="set RUN_ADMIN_BCRYPT_TEST=1 to run bcrypt hash verify",
)
def test_verify_admin_password_bcrypt(monkeypatch):
    # hash of "testpass" — generate once with passlib if this test is enabled
    from passlib.hash import bcrypt

    h = bcrypt.hash("testpass")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", h)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    from importlib import reload
    import auth.admin_auth as aa

    reload(aa)
    assert aa.verify_admin_password("testpass") is True
    assert aa.verify_admin_password("nope") is False
