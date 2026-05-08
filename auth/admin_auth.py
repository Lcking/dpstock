"""
Admin JWT (separate from end-user tokens).
Configure ADMIN_USERNAME + (ADMIN_PASSWORD_HASH bcrypt OR ADMIN_PASSWORD for bootstrap).
"""
from __future__ import annotations

import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt

from utils.logger import get_logger

logger = get_logger()

ADMIN_AUD = "admin"
ALGORITHM = "HS256"
ADMIN_TOKEN_HOURS = int(os.getenv("ADMIN_JWT_EXPIRE_HOURS", "8"))

_bearer = HTTPBearer(auto_error=False)


def _admin_secret() -> str:
    return os.getenv("ADMIN_JWT_SECRET") or os.getenv("JWT_SECRET_KEY") or secrets.token_hex(32)


def admin_login_configured() -> bool:
    user = (os.getenv("ADMIN_USERNAME") or "").strip()
    if not user:
        return False
    if (os.getenv("ADMIN_PASSWORD_HASH") or "").strip():
        return True
    if (os.getenv("ADMIN_PASSWORD") or "").strip():
        return True
    return False


def verify_admin_password(plain: str) -> bool:
    """Return True if password matches configured hash or plaintext env."""
    h = (os.getenv("ADMIN_PASSWORD_HASH") or "").strip()
    if h:
        try:
            return bcrypt.verify(plain, h)
        except Exception as e:
            logger.warning(f"[AdminAuth] bcrypt verify error: {e}")
            return False
    p = os.getenv("ADMIN_PASSWORD")
    if p is not None:
        return secrets.compare_digest(plain, p)
    return False


def create_admin_token() -> str:
    now = datetime.utcnow()
    payload = {
        "sub": "admin",
        "aud": ADMIN_AUD,
        "iat": now,
        "exp": now + timedelta(hours=ADMIN_TOKEN_HOURS),
    }
    return jwt.encode(payload, _admin_secret(), algorithm=ALGORITHM)


def decode_admin_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            _admin_secret(),
            algorithms=[ALGORITHM],
            audience=ADMIN_AUD,
        )
    except (JWTError, Exception):
        return None


# Simple in-memory rate limit: client_ip -> list of monotonic timestamps
_login_attempts: dict[str, list[float]] = {}
_LOGIN_WINDOW_S = 60.0
_LOGIN_MAX = 10


def _rate_limit_ok(client_host: str) -> bool:
    now = time.monotonic()
    bucket = _login_attempts.setdefault(client_host, [])
    while bucket and now - bucket[0] > _LOGIN_WINDOW_S:
        bucket.pop(0)
    if len(bucket) >= _LOGIN_MAX:
        return False
    bucket.append(now)
    return True


async def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="需要管理员登录")
    payload = decode_admin_token(credentials.credentials)
    if not payload or payload.get("sub") != "admin":
        raise HTTPException(status_code=401, detail="无效或过期的管理员令牌")
    return payload
