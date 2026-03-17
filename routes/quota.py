"""
Quota API Router
Handles quota status and quota checking endpoints
"""
from fastapi import APIRouter, Request, Response, HTTPException, Cookie
from typing import Optional
from pydantic import BaseModel
from datetime import date

from services.quota_service import QuotaService
from services.user_service import UserService
from routes.judgments import get_actor
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/v1", tags=["quota"])

# Initialize service
quota_service = QuotaService()
user_service = UserService()


def resolve_quota_user(request: Request, response: Response, aguai_uid: Optional[str]) -> str:
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
            key="aguai_uid",
            value=created_cookie_uid,
            max_age=365 * 24 * 60 * 60,
            httponly=True,
            samesite="lax"
        )
    user_service.migrate_identities_to_user(
        user_id=resolved["user_id"],
        anonymous_id=anonymous_id,
        cookie_uid=aguai_uid or created_cookie_uid,
        anchor_id=anchor_id,
    )
    return resolved["user_id"]


# Request/Response Models
class QuotaCheckRequest(BaseModel):
    """Request model for checking quota"""
    stock_code: str


class QuotaCheckResponse(BaseModel):
    """Response model for quota check"""
    allowed: bool
    reason: str
    remaining_quota: Optional[int] = None
    message: str
    analyzed_stocks_today: Optional[list] = None


@router.get("/quota/status")
async def get_quota_status(
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None)
):
    """
    Get current quota status for user
    
    Returns:
        - user_id: User ID
        - date: Current date
        - base_quota: Base daily quota (5)
        - invite_quota: Invite bonus quota
        - total_quota: Total available quota
        - used_quota: Quota used today
        - remaining_quota: Quota remaining
        - analyzed_stocks_today: List of stocks analyzed today
    """
    try:
        user_id = resolve_quota_user(request, response, aguai_uid)
        status = quota_service.get_quota_status(user_id)
        return status
        
    except Exception as e:
        logger.error(f"Failed to get quota status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "获取额度状态失败"
            }
        )


@router.post("/quota/check", response_model=QuotaCheckResponse)
async def check_quota(
    request_http: Request,
    response: Response,
    request: QuotaCheckRequest,
    aguai_uid: Optional[str] = Cookie(None)
):
    """
    Check if user can analyze a specific stock
    
    Args:
        stock_code: Stock code to check
        
    Returns:
        - allowed: Whether analysis is allowed
        - reason: Reason code (history/quota_available/quota_exceeded)
        - remaining_quota: Remaining quota (if applicable)
        - message: User-friendly message
        - analyzed_stocks_today: List of analyzed stocks (if quota exceeded)
    """
    try:
        user_id = resolve_quota_user(request_http, response, aguai_uid)
        allowed, reason, details = quota_service.check_quota(
            user_id=user_id,
            stock_code=request.stock_code
        )
        
        response = QuotaCheckResponse(
            allowed=allowed,
            reason=reason,
            message=details.get("message", ""),
            remaining_quota=details.get("remaining_quota"),
            analyzed_stocks_today=details.get("analyzed_stocks_today")
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to check quota: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "额度检查失败"
            }
        )
