"""
User Center API Routes — uses unified auth
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from auth.dependencies import get_current_user, UserContext
from services.user_service import UserService
from services.quota_service import QuotaService
from services.invite_service import InviteService
from services.watchlist import watchlist_service
from services.journal import journal_service
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/user-center", tags=["user-center"])

user_service = UserService()
quota_service = QuotaService()


def _mask_email(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return None
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


@router.get("/overview")
async def get_user_center_overview(user: UserContext = Depends(get_current_user)):
    try:
        user_record = user_service.get_user(user.user_id) or {}
        watchlists = watchlist_service.get_user_watchlists(user.user_id)
        recent_judgments = journal_service.get_records(user_id=user.user_id, page=1, page_size=5)
        due_count = journal_service.get_due_count(user.user_id)
        quota_status = quota_service.get_quota_status(user.user_id)

        return {
            "user": {
                "user_id": user.user_id,
                "is_temporary": user_service.is_temporary_user(user.user_id),
                "email_verified": bool(user_record.get("email_verified")),
                "masked_email": _mask_email(user_record.get("primary_email")),
                "status": user_record.get("status", "active"),
            },
            "quota_status": quota_status,
            "watchlist_count": len(watchlists),
            "watchlist_items_count": sum(int(w.items_count) for w in watchlists),
            "due_count": due_count,
            "recent_judgments": recent_judgments,
            "invite": {
                "reward_quota": InviteService.REWARD_QUOTA,
                "daily_limit": QuotaService.DAILY_INVITE_LIMIT,
            },
        }
    except Exception as e:
        logger.error(f"[UserCenter] Failed to load overview: {e}")
        raise HTTPException(status_code=500, detail="获取用户中心概览失败")
