"""
Watchlist API Routes
自选股列表 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Request, Response, Cookie
from typing import Optional, List
import uuid
from schemas.watchlist import (
    Watchlist, WatchlistCreate, WatchlistUpdate,
    WatchlistAddSymbols, WatchlistSummaryResponse
)
from services.watchlist import watchlist_service
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])

# Cookie settings (same as judgments)
COOKIE_NAME = "aguai_uid"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year


def get_actor(request: Request) -> dict:
    """
    Get actor identity from request
    Priority: 1. Bearer token (anchor) -> 2. X-Anonymous-Id header -> 3. Cookie
    Returns: {'type': 'anchor'|'anonymous', 'id': str}
    """
    # Check Authorization header for anchor token
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '')
        try:
            from services.anchor_service import AnchorService
            import os
            jwt_secret = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
            anchor_service = AnchorService(jwt_secret)
            anchor_id = anchor_service.verify_anchor_token(token)
            if anchor_id:
                return {'type': 'anchor', 'id': anchor_id}
        except Exception as e:
            logger.warning(f"Token verification failed: {str(e)}")
    
    # Check X-Anonymous-Id header
    anonymous_id = request.headers.get('X-Anonymous-Id')
    if anonymous_id:
        return {'type': 'anonymous', 'id': anonymous_id}
    
    return None


def get_or_create_user_id(request: Request, response: Response, aguai_uid: Optional[str] = None) -> str:
    """
    Get user ID from actor or cookie, create if needed
    """
    # First try actor (token or header)
    actor = get_actor(request)
    if actor:
        return actor['id']
    
    # Fallback to cookie
    if aguai_uid:
        return aguai_uid
    
    # Generate new user ID
    new_user_id = str(uuid.uuid4())
    response.set_cookie(
        key=COOKIE_NAME,
        value=new_user_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax"
    )
    logger.info(f"Created new watchlist user: {new_user_id[:8]}...")
    return new_user_id


@router.get("", response_model=List[Watchlist])
async def list_watchlists(
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None)
):
    """获取用户的所有自选股列表"""
    try:
        user_id = get_or_create_user_id(request, response, aguai_uid)
        return watchlist_service.get_user_watchlists(user_id)
    except Exception as e:
        logger.error(f"Error listing watchlists: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=Watchlist)
async def create_watchlist(
    data: WatchlistCreate,
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None)
):
    """创建自选股列表"""
    try:
        user_id = get_or_create_user_id(request, response, aguai_uid)
        return watchlist_service.create_watchlist(user_id, data)
    except Exception as e:
        logger.error(f"Error creating watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{watchlist_id}", response_model=Watchlist)
async def update_watchlist(
    watchlist_id: str,
    data: WatchlistUpdate,
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None)
):
    """更新自选股列表"""
    # TODO: 实现更新逻辑
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{watchlist_id}/symbols")
async def add_symbols(
    watchlist_id: str,
    data: WatchlistAddSymbols,
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None)
):
    """添加标的到自选股列表"""
    try:
        user_id = get_or_create_user_id(request, response, aguai_uid)
        # TODO: 验证 watchlist 属于当前用户
        added = watchlist_service.add_symbols(watchlist_id, data.ts_codes)
        return {"added": added, "total": len(data.ts_codes)}
    except Exception as e:
        logger.error(f"Error adding symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{watchlist_id}/symbols/{ts_code}")
async def remove_symbol(
    watchlist_id: str,
    ts_code: str,
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None)
):
    """从自选股列表移除标的"""
    try:
        user_id = get_or_create_user_id(request, response, aguai_uid)
        # TODO: 验证 watchlist 属于当前用户
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
    request: Request,
    response: Response,
    asof: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
    sort: str = Query("SCORE_DESC", description="排序方式"),
    filters: Optional[str] = Query(None, description="过滤条件，逗号分隔"),
    aguai_uid: Optional[str] = Cookie(None)
):
    """
    获取自选股批量摘要
    
    PRD 强制: 批量接口，避免逐只触发 analysis 风暴
    """
    try:
        user_id = get_or_create_user_id(request, response, aguai_uid)
        # TODO: 验证 watchlist 属于当前用户
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
