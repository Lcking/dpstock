"""
Compare API Routes
比较分桶 API 端点
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from services.compare import compare_service
from schemas.watchlist import WatchlistItemSummary
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(tags=["compare"])


class CompareRequest(BaseModel):
    """比较请求"""
    ts_codes: List[str] = Field(..., min_length=2, max_length=20, description="股票代码列表")
    asof: Optional[str] = Field(None, description="日期 YYYY-MM-DD")
    window: int = Field(20, ge=5, le=60, description="窗口期")
    bench: str = Field("000300.SH", description="基准指数")
    use_industry: bool = Field(True, description="是否使用行业基准")
    constraints: Optional[Dict[str, Any]] = Field(None, description="约束条件")


class BucketResponse(BaseModel):
    """桶响应"""
    id: str
    title: str
    reason: str
    items: List[WatchlistItemSummary]


class CompareResponse(BaseModel):
    """比较响应"""
    meta: Dict[str, Any]
    buckets: List[BucketResponse]


@router.post("/api/compare", response_model=CompareResponse)
async def compare_stocks(request: CompareRequest):
    """
    比较标的并分桶
    
    返回四桶看板:
    - best: 结构占优
    - conflict: 信号冲突  
    - weak: 结构偏弱
    - event: 事件扰动
    """
    try:
        result = compare_service.compare(
            ts_codes=request.ts_codes,
            asof=request.asof,
            window=request.window,
            bench=request.bench,
            use_industry=request.use_industry
        )
        
        return CompareResponse(
            meta=result.meta,
            buckets=[
                BucketResponse(
                    id=b.id,
                    title=b.title,
                    reason=b.reason,
                    items=b.items
                )
                for b in result.buckets
            ]
        )
    except Exception as e:
        logger.error(f"Compare error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
