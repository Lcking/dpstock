"""
Anchor API Routes — Email Binding and Verification

After successful email binding, returns a **unified JWT** (same format
as the login token) so the frontend only needs to store one token.
"""

from fastapi import APIRouter, Request, Header, HTTPException, Cookie
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import re

from auth.dependencies import (
    get_current_user,
    create_user_token,
    UserContext,
    SECRET_KEY,
)
from services.anchor_service import AnchorService
from services.journal import journal_service
from services.user_service import UserService
from utils.logger import get_logger

logger = get_logger()

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
anchor_service = AnchorService(JWT_SECRET)
user_service = UserService()

# ============ Request/Response Models ============


class SendCodeRequest(BaseModel):
    email: EmailStr


class SendCodeResponse(BaseModel):
    ok: bool
    message: str


class VerifyAndBindRequest(BaseModel):
    email: EmailStr
    code: str


class VerifyAndBindResponse(BaseModel):
    anchor_id: str
    token: str
    migrated_count: int
    masked_email: str


class AnchorStatusResponse(BaseModel):
    mode: str  # 'anonymous' or 'anchor'
    masked_email: Optional[str] = None


# ============ Helper Functions ============


def validate_email_format(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def _get_actor_from_request(request: Request) -> dict:
    """
    Lightweight actor extraction for the anchor status endpoint.
    Uses the unified auth module internally.
    """
    # Check X-Anchor-Token (legacy) or Authorization Bearer
    for header_name in ("X-Anchor-Token", "Authorization"):
        value = request.headers.get(header_name, "")
        if header_name == "Authorization" and value.startswith("Bearer "):
            value = value[7:]
        if not value:
            continue
        anchor_id = anchor_service.verify_anchor_token(value)
        if anchor_id:
            return {"type": "anchor", "id": anchor_id}

    anonymous_id = request.headers.get("X-Anonymous-Id")
    if anonymous_id:
        return {"type": "anonymous", "id": anonymous_id}

    import uuid
    temp_id = str(uuid.uuid4())
    logger.warning(f"请求缺少身份标识,生成临时ID: {temp_id}")
    return {"type": "anonymous", "id": temp_id}


# ============ API Endpoints ============


@router.post("/api/anchor/send_code", response_model=SendCodeResponse)
async def send_verification_code(request: SendCodeRequest):
    email = request.email.lower().strip()

    if not validate_email_format(email):
        raise HTTPException(status_code=400, detail="邮箱格式无效")

    email_hash = anchor_service.hash_email(email)
    email_masked = anchor_service.mask_email(email)

    allowed, error_msg = anchor_service.check_send_code_rate_limit(email_hash)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)

    code = anchor_service.generate_code()
    anchor_service.save_verification_code(email_hash, code)

    from services.email_service import send_verification_code as send_email

    success, message = send_email(email, code, email_masked)
    if not success:
        logger.warning(f"Email send failed for {email_masked}, but code is saved")

    return SendCodeResponse(ok=True, message=message)


@router.post("/api/anchor/verify_and_bind", response_model=VerifyAndBindResponse)
async def verify_and_bind(
    request: VerifyAndBindRequest,
    x_anonymous_id: Optional[str] = Header(None, alias="X-Anonymous-Id"),
    aguai_uid: Optional[str] = Cookie(None),
):
    if not x_anonymous_id:
        raise HTTPException(status_code=400, detail="缺少 X-Anonymous-Id header,无法绑定")

    email = request.email.lower().strip()
    code = request.code.strip()

    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=400, detail="验证码格式错误")

    email_hash = anchor_service.hash_email(email)

    valid, error_msg = anchor_service.verify_code(email_hash, code)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)

    anchor_id = anchor_service.get_or_create_anchor(email)
    target_user_id = user_service.bind_email_identity(
        anonymous_id=x_anonymous_id,
        cookie_uid=aguai_uid,
        anchor_id=anchor_id,
        email=email,
    )

    migrated_count = anchor_service.migrate_anonymous_to_anchor(
        anonymous_id=x_anonymous_id,
        anchor_id=anchor_id,
    )

    # Issue a unified token (replaces the old separate anchor token)
    token = create_user_token(
        user_id=target_user_id,
        identity_type="email_anchor",
        anchor_id=anchor_id,
        sub="user",
    )

    masked_email = anchor_service.mask_email(email)

    logger.info(
        f"绑定成功: anonymous={x_anonymous_id} -> user={target_user_id}, "
        f"anchor={anchor_id}, migrated={migrated_count}"
    )

    return VerifyAndBindResponse(
        anchor_id=anchor_id,
        token=token,
        migrated_count=migrated_count,
        masked_email=masked_email,
    )


@router.get("/api/anchor/status", response_model=AnchorStatusResponse)
async def get_anchor_status(request: Request):
    actor = _get_actor_from_request(request)

    if actor["type"] == "anchor":
        anchor = anchor_service.get_anchor_by_id(actor["id"])
        if anchor:
            return AnchorStatusResponse(
                mode="anchor",
                masked_email=anchor.get("anchor_value_masked"),
            )

    return AnchorStatusResponse(mode="anonymous")


@router.post("/api/anchor/cleanup")
async def cleanup_expired_codes():
    deleted_count = anchor_service.cleanup_expired_codes()
    return {"ok": True, "deleted_count": deleted_count}
