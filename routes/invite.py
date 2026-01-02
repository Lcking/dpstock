"""
Invite API Router
Handles invite code generation and acceptance
"""
from fastapi import APIRouter, Request, Response, HTTPException, Cookie
from typing import Optional
from pydantic import BaseModel
import uuid

from services.invite_service import InviteService
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/v1", tags=["invite"])

# Initialize service
invite_service = InviteService()

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
    aguai_uid: Optional[str] = Cookie(None)
):
    """
    Generate invite code for user
    
    Returns:
        - invite_code: Generated or existing invite code
        - invite_url: Full invite URL
        - message: User-friendly message
    """
    if not aguai_uid:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthorized",
                "message": "请先访问首页以获取用户身份"
            }
        )
    
    try:
        result = invite_service.generate_invite_code(aguai_uid)
        
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
        
        # Check if user already has aguai_uid
        if not aguai_uid:
            # Create new user ID
            aguai_uid = str(uuid.uuid4())
            response.set_cookie(
                key=COOKIE_NAME,
                value=aguai_uid,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax"
            )
            logger.info(f"Created new user via invite: {aguai_uid}")
        
        # Set referrer cookie (will be used to trigger reward after first analysis)
        response.set_cookie(
            key=REFERRER_COOKIE,
            value=inviter_id,
            max_age=30 * 24 * 60 * 60,  # 30 days
            httponly=True,
            samesite="lax"
        )
        
        logger.info(f"Accepted invite: invitee={aguai_uid}, inviter={inviter_id}, code={code}")
        
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
