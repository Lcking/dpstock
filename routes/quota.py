"""
Quota API Router — uses unified auth
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
from pydantic import BaseModel

from auth.dependencies import get_current_user, UserContext
from services.analyze_spend_guard import AnalyzeSpendGuard, SpendGuardUnavailable
from services.client_ip import resolve_client_ip
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
async def get_quota_status(
    request: Request,
    user: UserContext = Depends(get_current_user),
):
    try:
        if not user.is_authenticated:
            return AnalyzeSpendGuard().status(
                client_ip=resolve_client_ip(request),
                user_id=user.user_id,
            )
        return quota_service.get_quota_status(
            user.user_id,
            is_authenticated=True,
        )
    except Exception as e:
        logger.error(f"Failed to get quota status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "获取额度状态失败"},
        )


@router.post("/quota/check", response_model=QuotaCheckResponse)
async def check_quota(
    request: QuotaCheckRequest,
    http_request: Request,
    user: UserContext = Depends(get_current_user),
):
    try:
        if not user.is_authenticated:
            try:
                allowed, reason, details = AnalyzeSpendGuard().peek(
                    client_ip=resolve_client_ip(http_request),
                    stock_code=request.stock_code,
                    user_id=user.user_id,
                )
            except SpendGuardUnavailable:
                raise HTTPException(
                    status_code=503,
                    detail={"error": "spend_guard_unavailable", "message": "额度检查暂时不可用"},
                )
        else:
            allowed, reason, details = quota_service.check_quota(
                user_id=user.user_id,
                stock_code=request.stock_code,
                is_authenticated=True,
            )
        return QuotaCheckResponse(
            allowed=allowed,
            reason=reason,
            message=details.get("message", ""),
            remaining_quota=details.get("remaining_quota"),
            analyzed_stocks_today=details.get("analyzed_stocks_today"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check quota: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "额度检查失败"},
        )
