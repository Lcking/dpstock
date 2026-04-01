"""
Quota API Router — uses unified auth
"""
from fastapi import APIRouter, HTTPException, Depends, Cookie
from typing import Optional
from pydantic import BaseModel

from auth.dependencies import get_current_user, UserContext
from services.quota_service import QuotaService
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/v1", tags=["quota"])

quota_service = QuotaService()


class QuotaCheckRequest(BaseModel):
    stock_code: str


class QuotaCheckResponse(BaseModel):
    allowed: bool
    reason: str
    remaining_quota: Optional[int] = None
    message: str
    analyzed_stocks_today: Optional[list] = None


@router.get("/quota/status")
async def get_quota_status(user: UserContext = Depends(get_current_user)):
    try:
        return quota_service.get_quota_status(user.user_id)
    except Exception as e:
        logger.error(f"Failed to get quota status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "获取额度状态失败"},
        )


@router.post("/quota/check", response_model=QuotaCheckResponse)
async def check_quota(
    request: QuotaCheckRequest,
    user: UserContext = Depends(get_current_user),
):
    try:
        allowed, reason, details = quota_service.check_quota(
            user_id=user.user_id,
            stock_code=request.stock_code,
        )
        return QuotaCheckResponse(
            allowed=allowed,
            reason=reason,
            message=details.get("message", ""),
            remaining_quota=details.get("remaining_quota"),
            analyzed_stocks_today=details.get("analyzed_stocks_today"),
        )
    except Exception as e:
        logger.error(f"Failed to check quota: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "额度检查失败"},
        )
