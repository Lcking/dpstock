"""
Watchlist API Routes
自选股列表 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from schemas.watchlist import (
    Watchlist, WatchlistCreate, WatchlistUpdate,
    WatchlistAddSymbols, WatchlistSummaryResponse
)
from services.watchlist import watchlist_service
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])


def get_current_user_id() -> str:
    """获取当前用户ID (暂时使用匿名ID)"""
    # TODO: 从JWT/session获取真实用户ID
    return "anonymous"


@router.get("", response_model=List[Watchlist])
async def list_watchlists(user_id: str = Depends(get_current_user_id)):
    """获取用户的所有自选股列表"""
    try:
        return watchlist_service.get_user_watchlists(user_id)
    except Exception as e:
        logger.error(f"Error listing watchlists: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=Watchlist)
async def create_watchlist(
    data: WatchlistCreate,
    user_id: str = Depends(get_current_user_id)
):
    """创建自选股列表"""
    try:
        return watchlist_service.create_watchlist(user_id, data)
    except Exception as e:
        logger.error(f"Error creating watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{watchlist_id}", response_model=Watchlist)
async def update_watchlist(
    watchlist_id: str,
    data: WatchlistUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """更新自选股列表"""
    # TODO: 实现更新逻辑
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{watchlist_id}/symbols")
async def add_symbols(
    watchlist_id: str,
    data: WatchlistAddSymbols,
    user_id: str = Depends(get_current_user_id)
):
    """添加标的到自选股列表"""
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
    user_id: str = Depends(get_current_user_id)
):
    """从自选股列表移除标的"""
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


@router.get("/{watchlist_id}/summary", response_model=WatchlistSummaryResponse)
async def get_summary(
    watchlist_id: str,
    asof: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
    sort: str = Query("SCORE_DESC", description="排序方式"),
    filters: Optional[str] = Query(None, description="过滤条件，逗号分隔"),
    user_id: str = Depends(get_current_user_id)
):
    """
    获取自选股批量摘要
    
    PRD 强制: 批量接口，避免逐只触发 analysis 风暴
    """
    try:
        filter_list = filters.split(",") if filters else []
        return watchlist_service.get_summary(
            watchlist_id=watchlist_id,
            asof=asof,
            sort=sort,
            filters=filter_list
        )
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
