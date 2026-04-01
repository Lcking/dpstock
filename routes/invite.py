"""
Invite API Router — uses unified auth
"""
from fastapi import APIRouter, Request, Response, HTTPException, Cookie, Depends
from typing import Optional
from pydantic import BaseModel

from auth.dependencies import get_current_user, UserContext
from services.invite_service import InviteService
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/v1", tags=["invite"])

invite_service = InviteService()

REFERRER_COOKIE = "aguai_ref"


class InviteGenerateResponse(BaseModel):
    invite_code: str
    invite_url: str
    message: str


class InviteAcceptResponse(BaseModel):
    success: bool
    message: str
    inviter_bonus_pending: Optional[bool] = None
    error: Optional[str] = None


@router.post("/invite/generate", response_model=InviteGenerateResponse)
async def generate_invite_code(
    request: Request,
    user: UserContext = Depends(get_current_user),
):
    try:
        result = invite_service.generate_invite_code(user.user_id)
        base_url = str(request.base_url).rstrip("/")
        invite_url = f"{base_url}/?invite={result['invite_code']}"

        message = "邀请链接已生成！分享给朋友，TA 完成首次分析后，您将获得 +5 次额度"
        if not result["is_new"]:
            message = "您的邀请链接（已存在）"

        return InviteGenerateResponse(
            invite_code=result["invite_code"],
            invite_url=invite_url,
            message=message,
        )
    except Exception as e:
        logger.error(f"Failed to generate invite code: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "生成邀请码失败"},
        )


@router.get("/invite/accept", response_model=InviteAcceptResponse)
async def accept_invite(
    code: str,
    response: Response,
    user: UserContext = Depends(get_current_user),
):
    try:
        inviter_id = invite_service.validate_invite_code(code)
        if not inviter_id:
            return InviteAcceptResponse(
                success=False,
                error="invalid_code",
                message="邀请码无效或已过期",
            )

        response.set_cookie(
            key=REFERRER_COOKIE,
            value=inviter_id,
            max_age=30 * 24 * 60 * 60,
            httponly=True,
            samesite="lax",
        )

        logger.info(f"Accepted invite: invitee={user.user_id}, inviter={inviter_id}, code={code}")

        return InviteAcceptResponse(
            success=True,
            message="欢迎！您已通过邀请加入",
            inviter_bonus_pending=True,
        )
    except Exception as e:
        logger.error(f"Failed to accept invite: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "接受邀请失败"},
        )
