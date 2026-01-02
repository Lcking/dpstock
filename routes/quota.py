"""
Quota API Router
Handles quota status and quota checking endpoints
"""
from fastapi import APIRouter, Request, Response, HTTPException, Cookie
from typing import Optional
from pydantic import BaseModel
from datetime import date

from services.quota_service import QuotaService
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/v1", tags=["quota"])

# Initialize service
quota_service = QuotaService()


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
    if not aguai_uid:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthorized",
                "message": "请先访问首页以获取用户身份"
            }
        )
    
    try:
        status = quota_service.get_quota_status(aguai_uid)
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
    if not aguai_uid:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthorized",
                "message": "请先访问首页以获取用户身份"
            }
        )
    
    try:
        allowed, reason, details = quota_service.check_quota(
            user_id=aguai_uid,
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
