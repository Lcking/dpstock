"""
Unified authentication & identity resolution.

Single source of truth for:
 1. Issuing JWTs  (create_user_token)
 2. Resolving the current user from any HTTP request (get_current_user)
 3. Enforcing the optional password-login gate (require_login)

Token payload (unified format):
  {
    "sub":            "user" | "guest",        # backward compat with login flow
    "user_id":        "<uuid>",                # canonical user id from `users` table
    "identity_type":  "email_anchor" | "anonymous" | "cookie_uid" | "login",
    "anchor_id":      "<uuid>" | null,         # only for email-bound users
    "exp":            <timestamp>,
    "iat":            <timestamp>
  }

Resolution order (get_current_user):
  Authorization: Bearer <token>  →  X-Anonymous-Id  →  aguai_uid cookie  →  create new

Future identity types (phone, wechat_openid, …) are handled identically —
just a new `identity_type` string + the same token format.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, Response
from jose import JWTError, jwt

from services.user_service import UserService
from utils.logger import get_logger

logger = get_logger()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "")
REQUIRE_LOGIN = bool(LOGIN_PASSWORD.strip())

COOKIE_NAME = "aguai_uid"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year

_user_service: Optional[UserService] = None


def _get_user_service() -> UserService:
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service


# ---------------------------------------------------------------------------
# UserContext — the unified result every route receives
# ---------------------------------------------------------------------------
@dataclass
class UserContext:
    user_id: str
    identity_type: str  # "email_anchor" | "anonymous" | "cookie_uid" | "login"
    is_authenticated: bool = False  # True when email-bound or password-logged-in
    anchor_id: Optional[str] = None
    masked_email: Optional[str] = None


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------
def create_user_token(
    *,
    user_id: str,
    identity_type: str,
    anchor_id: Optional[str] = None,
    sub: str = "user",
    expire_days: int = TOKEN_EXPIRE_DAYS,
) -> str:
    """Issue a single unified JWT."""
    now = datetime.utcnow()
    payload: dict = {
        "sub": sub,
        "user_id": user_id,
        "identity_type": identity_type,
        "iat": now,
        "exp": now + timedelta(days=expire_days),
    }
    if anchor_id:
        payload["anchor_id"] = anchor_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> Optional[dict]:
    """Decode JWT. Returns payload dict or None on any failure."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except (JWTError, Exception):
        return None


def _resolve_legacy_anchor_token(token: str) -> Optional[dict]:
    """
    Handle old-format anchor tokens (payload: {"anchor_id": "…"}).
    Converts to a UserContext-compatible dict with user_id.
    """
    try:
        import pyjwt_decode
    except ImportError:
        pass

    payload = _decode_token(token)
    if not payload:
        return None

    anchor_id = payload.get("anchor_id")
    if not anchor_id or payload.get("user_id"):
        return None

    svc = _get_user_service()
    try:
        user_id = svc.get_or_create_user_by_identity(
            identity_type="email_anchor",
            identity_value=anchor_id,
        )
        return {
            "user_id": user_id,
            "identity_type": "email_anchor",
            "anchor_id": anchor_id,
            "is_authenticated": True,
        }
    except Exception as e:
        logger.warning(f"[Auth] Legacy anchor token resolution failed: {e}")
        return None


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------
async def get_current_user(
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None),
) -> UserContext:
    """
    Unified dependency — resolves the current user from any HTTP request.

    Works whether or not REQUIRE_LOGIN is enabled.  When login is required
    but no valid token is present, falls through to anonymous resolution
    (the ``require_login`` wrapper handles the 401).
    """
    svc = _get_user_service()

    # --- 1. Authorization: Bearer <token> ----------------------------------
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = _decode_token(token)

        if payload:
            # New unified format (has user_id)
            if payload.get("user_id"):
                ctx = UserContext(
                    user_id=payload["user_id"],
                    identity_type=payload.get("identity_type", "login"),
                    is_authenticated=payload.get("identity_type") in (
                        "email_anchor", "login", "phone", "wechat_openid",
                    ),
                    anchor_id=payload.get("anchor_id"),
                )
                _ensure_identity_migrated(svc, ctx, anonymous_id=request.headers.get("X-Anonymous-Id"), cookie_uid=aguai_uid)
                return ctx

            # Old login format (has "sub" but no user_id) — resolve identity
            if payload.get("sub") in ("user", "guest"):
                return await _resolve_from_headers(
                    svc, request, response, aguai_uid, login_sub=payload.get("sub"),
                )

            # Old anchor format (has anchor_id only)
            legacy = _resolve_legacy_anchor_token(token)
            if legacy:
                ctx = UserContext(**legacy)
                _ensure_identity_migrated(svc, ctx, anonymous_id=request.headers.get("X-Anonymous-Id"), cookie_uid=aguai_uid)
                return ctx

    # --- 2-4. No valid Bearer token — resolve from headers / cookie --------
    return await _resolve_from_headers(svc, request, response, aguai_uid)


async def require_login(
    user: UserContext = Depends(get_current_user),
    request: Request = None,
) -> UserContext:
    """
    Wraps ``get_current_user`` and enforces the password-login gate.

    When ``REQUIRE_LOGIN`` is False this is a pass-through.
    When True, only tokens with ``sub == "user"`` (i.e. password-authenticated)
    are accepted.
    """
    if not REQUIRE_LOGIN:
        return user

    auth_header = (request.headers.get("Authorization", "") if request else "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证凭据")

    token = auth_header[7:]
    payload = _decode_token(token)
    if not payload or payload.get("sub") != "user":
        raise HTTPException(status_code=401, detail="无效的认证凭据")

    return user


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
async def _resolve_from_headers(
    svc: UserService,
    request: Request,
    response: Response,
    aguai_uid: Optional[str],
    login_sub: Optional[str] = None,
) -> UserContext:
    """Resolve user from X-Anonymous-Id header → cookie → create new."""

    anonymous_id = request.headers.get("X-Anonymous-Id")

    # Try anonymous header
    if anonymous_id:
        resolved = svc.resolve_request_user(anonymous_id=anonymous_id)
        ctx = UserContext(
            user_id=resolved["user_id"],
            identity_type="anonymous",
            is_authenticated=False,
        )
        _ensure_identity_migrated(svc, ctx, anonymous_id=anonymous_id, cookie_uid=aguai_uid)
        return ctx

    # Try cookie
    if aguai_uid:
        resolved = svc.resolve_request_user(cookie_uid=aguai_uid)
        ctx = UserContext(
            user_id=resolved["user_id"],
            identity_type="cookie_uid",
            is_authenticated=False,
        )
        _ensure_identity_migrated(svc, ctx, cookie_uid=aguai_uid)
        return ctx

    # Create new (set cookie)
    resolved = svc.resolve_request_user(create_missing_cookie=True)
    created = resolved.get("created_cookie_uid")
    if created:
        response.set_cookie(
            key=COOKIE_NAME,
            value=created,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
    return UserContext(
        user_id=resolved["user_id"],
        identity_type="cookie_uid",
        is_authenticated=False,
    )


def _ensure_identity_migrated(
    svc: UserService,
    ctx: UserContext,
    *,
    anonymous_id: Optional[str] = None,
    cookie_uid: Optional[str] = None,
) -> None:
    """Best-effort asset migration (non-blocking)."""
    try:
        svc.migrate_identities_to_user(
            user_id=ctx.user_id,
            anonymous_id=anonymous_id,
            cookie_uid=cookie_uid,
            anchor_id=ctx.anchor_id,
        )
    except Exception as e:
        logger.warning(f"[Auth] Identity migration skipped: {e}")
