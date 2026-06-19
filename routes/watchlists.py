"""
Watchlist API Routes
自选股列表 API 端点 — uses unified auth
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List

from auth.dependencies import get_current_user, UserContext
from schemas.watchlist import (
    Watchlist, WatchlistCreate, WatchlistUpdate,
    WatchlistAddSymbols, WatchlistSummaryResponse, WatchlistSymbolWeightUpdate,
)
from services.watchlist import watchlist_service
from services.watchlist_risk_alert_service import WatchlistRiskAlertService
from utils.logger import get_logger

logger = get_logger()


def _watchlist_risk_alert_service() -> WatchlistRiskAlertService:
    return WatchlistRiskAlertService()

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])


def _resolve_watchlist_user(user: UserContext) -> str:
    """Resolve canonical watchlist user, with single-bound-user fallback for legacy sessions."""
    if user.is_authenticated:
        return user.user_id

    try:
        fallback_user_id = watchlist_service.get_single_bound_user_id_with_watchlists()
        if fallback_user_id:
            anon_count = watchlist_service.get_watchlists_count(user.user_id)
            bound_count = watchlist_service.get_watchlists_count(fallback_user_id)
            if anon_count == 0 and bound_count > 0:
                logger.info("[Watchlist] Fallback to single bound user for anonymous session")
                return fallback_user_id
    except Exception as e:
        logger.warning(f"[Watchlist] Bound user fallback skipped: {e}")

    return user.user_id


@router.get("", response_model=List[Watchlist])
async def list_watchlists(user: UserContext = Depends(get_current_user)):
    try:
        return watchlist_service.get_user_watchlists(_resolve_watchlist_user(user))
    except Exception as e:
        logger.error(f"Error listing watchlists: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=Watchlist)
async def create_watchlist(
    data: WatchlistCreate,
    user: UserContext = Depends(get_current_user),
):
    try:
        return watchlist_service.create_watchlist(_resolve_watchlist_user(user), data)
    except Exception as e:
        logger.error(f"Error creating watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-alerts/unread-count")
async def get_risk_alert_unread_count(user: UserContext = Depends(get_current_user)):
    try:
        user_id = _resolve_watchlist_user(user)
        return {"count": _watchlist_risk_alert_service().get_unread_count(user_id)}
    except Exception as e:
        logger.error(f"Error getting risk alert unread count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-alerts")
async def list_risk_alerts(
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    user: UserContext = Depends(get_current_user),
):
    try:
        user_id = _resolve_watchlist_user(user)
        return _watchlist_risk_alert_service().list_alerts(
            user_id=user_id,
            limit=limit,
            unread_only=unread_only,
        )
    except Exception as e:
        logger.error(f"Error listing risk alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk-alerts/mark-read")
async def mark_risk_alerts_read(user: UserContext = Depends(get_current_user)):
    try:
        user_id = _resolve_watchlist_user(user)
        return _watchlist_risk_alert_service().mark_all_read(user_id)
    except Exception as e:
        logger.error(f"Error marking risk alerts read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{watchlist_id}", response_model=Watchlist)
async def update_watchlist(
    watchlist_id: str,
    data: WatchlistUpdate,
    user: UserContext = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{watchlist_id}/symbols")
async def add_symbols(
    watchlist_id: str,
    data: WatchlistAddSymbols,
    user: UserContext = Depends(get_current_user),
):
    try:
        added = watchlist_service.add_symbols(watchlist_id, data.ts_codes)
        return {"added": added, "total": len(data.ts_codes)}
    except Exception as e:
        logger.error(f"Error adding symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{watchlist_id}/symbols/{ts_code}")
async def remove_symbol(
    watchlist_id: str,
    ts_code: str,
    user: UserContext = Depends(get_current_user),
):
    try:
        removed = watchlist_service.remove_symbol(watchlist_id, ts_code)
        if not removed:
            raise HTTPException(status_code=404, detail="Symbol not found")
        return {"removed": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing symbol: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{watchlist_id}/symbols/{ts_code}/weight")
async def update_symbol_weight(
    watchlist_id: str,
    ts_code: str,
    data: WatchlistSymbolWeightUpdate,
    user: UserContext = Depends(get_current_user),
):
    try:
        updated = watchlist_service.update_symbol_weight(
            watchlist_id,
            ts_code,
            data.weight_pct,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Symbol not found")
        return {"updated": True, "weight_pct": data.weight_pct}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating symbol weight: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{watchlist_id}/summary", response_model=WatchlistSummaryResponse)
async def get_summary(
    watchlist_id: str,
    asof: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
    sort: str = Query("SCORE_DESC", description="排序方式"),
    filters: Optional[str] = Query(None, description="过滤条件，逗号分隔"),
    user: UserContext = Depends(get_current_user),
):
    try:
        filter_list = filters.split(",") if filters else []
        return watchlist_service.get_summary(
            watchlist_id=watchlist_id,
            asof=asof,
            sort=sort,
            filters=filter_list,
        )
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
