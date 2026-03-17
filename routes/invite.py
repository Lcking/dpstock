"""
Invite API Router
Handles invite code generation and acceptance
"""
from fastapi import APIRouter, Request, Response, HTTPException, Cookie
from typing import Optional
from pydantic import BaseModel

from services.invite_service import InviteService
from services.user_service import UserService
from routes.judgments import get_actor
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/v1", tags=["invite"])

# Initialize service
invite_service = InviteService()
user_service = UserService()

# Cookie settings
COOKIE_NAME = "aguai_uid"
REFERRER_COOKIE = "aguai_ref"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year


# Response Models
class InviteGenerateResponse(BaseModel):
    """Response model for invite generation"""
    invite_code: str
    invite_url: str
    message: str


class InviteAcceptResponse(BaseModel):
    """Response model for invite acceptance"""
    success: bool
    message: str
    inviter_bonus_pending: Optional[bool] = None
    error: Optional[str] = None


@router.post("/invite/generate", response_model=InviteGenerateResponse)
async def generate_invite_code(
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None)
):
    """
    Generate invite code for user
    
    Returns:
        - invite_code: Generated or existing invite code
        - invite_url: Full invite URL
        - message: User-friendly message
    """
    try:
        actor = get_actor(request)
        anchor_id = actor["id"] if actor and actor.get("type") == "anchor" else None
        anonymous_id = actor["id"] if actor and actor.get("type") == "anonymous" else None
        resolved = user_service.resolve_request_user(
            anchor_id=anchor_id,
            anonymous_id=anonymous_id,
            cookie_uid=aguai_uid,
            create_missing_cookie=not actor and not aguai_uid,
        )
        created_cookie_uid = resolved.get("created_cookie_uid")
        if created_cookie_uid:
            response.set_cookie(
                key=COOKIE_NAME,
                value=created_cookie_uid,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax"
            )
            logger.info(f"Created user identity during invite generation: {created_cookie_uid}")
        user_service.migrate_identities_to_user(
            user_id=resolved["user_id"],
            anonymous_id=anonymous_id,
            cookie_uid=aguai_uid or created_cookie_uid,
            anchor_id=anchor_id,
        )

        result = invite_service.generate_invite_code(resolved["user_id"])
        
        # Build invite URL
        base_url = str(request.base_url).rstrip('/')
        invite_url = f"{base_url}/?invite={result['invite_code']}"
        
        message = "邀请链接已生成！分享给朋友，TA 完成首次分析后，您将获得 +5 次额度"
        if not result['is_new']:
            message = "您的邀请链接（已存在）"
        
        return InviteGenerateResponse(
            invite_code=result['invite_code'],
            invite_url=invite_url,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Failed to generate invite code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "生成邀请码失败"
            }
        )


@router.get("/invite/accept", response_model=InviteAcceptResponse)
async def accept_invite(
    code: str,
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None)
):
    """
    Accept invite code (set referrer cookie)
    
    Args:
        code: Invite code from URL parameter
        
    Returns:
        - success: Whether invite was accepted
        - message: User-friendly message
        - inviter_bonus_pending: Whether bonus will be granted after first analysis
    """
    try:
        # Validate invite code
        inviter_id = invite_service.validate_invite_code(code)
        
        if not inviter_id:
            return InviteAcceptResponse(
                success=False,
                error="invalid_code",
                message="邀请码无效或已过期"
            )
        
        actor = get_actor(request)
        anchor_id = actor["id"] if actor and actor.get("type") == "anchor" else None
        anonymous_id = actor["id"] if actor and actor.get("type") == "anonymous" else None
        resolved = user_service.resolve_request_user(
            anchor_id=anchor_id,
            anonymous_id=anonymous_id,
            cookie_uid=aguai_uid,
            create_missing_cookie=not actor and not aguai_uid,
        )
        created_cookie_uid = resolved.get("created_cookie_uid")
        if created_cookie_uid:
            response.set_cookie(
                key=COOKIE_NAME,
                value=created_cookie_uid,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax"
            )
            logger.info(f"Created new user via invite: {created_cookie_uid}")

        user_service.migrate_identities_to_user(
            user_id=resolved["user_id"],
            anonymous_id=anonymous_id,
            cookie_uid=aguai_uid or created_cookie_uid,
            anchor_id=anchor_id,
        )
        
        # Set referrer cookie (will be used to trigger reward after first analysis)
        response.set_cookie(
            key=REFERRER_COOKIE,
            value=inviter_id,
            max_age=30 * 24 * 60 * 60,  # 30 days
            httponly=True,
            samesite="lax"
        )
        
        logger.info(f"Accepted invite: invitee={resolved['user_id']}, inviter={inviter_id}, code={code}")
        
        return InviteAcceptResponse(
            success=True,
            message="欢迎！您已通过邀请加入",
            inviter_bonus_pending=True
        )
        
    except Exception as e:
        logger.error(f"Failed to accept invite: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "接受邀请失败"
            }
        )
