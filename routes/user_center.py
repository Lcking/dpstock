"""
User Center API Routes
"""
from fastapi import APIRouter, HTTPException, Request, Response, Cookie
from typing import Optional

from routes.judgments import get_actor
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

COOKIE_NAME = "aguai_uid"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60


def _mask_email(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return None
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def resolve_current_user(request: Request, response: Response, aguai_uid: Optional[str]) -> str:
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
            samesite="lax",
        )

    user_service.migrate_identities_to_user(
        user_id=resolved["user_id"],
        anonymous_id=anonymous_id,
        cookie_uid=aguai_uid or created_cookie_uid,
        anchor_id=anchor_id,
    )
    return resolved["user_id"]


@router.get("/overview")
async def get_user_center_overview(
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None),
):
    try:
        user_id = resolve_current_user(request, response, aguai_uid)
        user = user_service.get_user(user_id) or {}
        watchlists = watchlist_service.get_user_watchlists(user_id)
        recent_judgments = journal_service.get_records(user_id=user_id, page=1, page_size=5)
        due_count = journal_service.get_due_count(user_id)
        quota_status = quota_service.get_quota_status(user_id)

        return {
            "user": {
                "user_id": user_id,
                "is_temporary": user_service.is_temporary_user(user_id),
                "email_verified": bool(user.get("email_verified")),
                "masked_email": _mask_email(user.get("primary_email")),
                "status": user.get("status", "active"),
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
