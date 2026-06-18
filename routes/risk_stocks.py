"""
Risk stock list API routes.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from auth.admin_auth import require_admin
from services.risk_stock_service import RiskStockService


router = APIRouter(prefix="/api/risk-stocks", tags=["risk-stocks"])
admin_router = APIRouter(prefix="/api/admin/risk-stocks", tags=["admin-risk-stocks"])


class RiskStockRefreshRequest(BaseModel):
    trade_date: str = Field(..., description="交易日 YYYYMMDD")
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = "manual"


def _serialize_item(row: Dict[str, Any]) -> Dict[str, Any]:
    import json

    item = dict(row)
    try:
        item["tags"] = json.loads(item.get("tags_json") or "[]")
    except Exception:
        item["tags"] = []
    return item


def _risk_stock_service() -> RiskStockService:
    return RiskStockService()


@router.get("")
async def list_risk_stocks(
    trade_date: Optional[str] = Query(None, description="交易日 YYYYMMDD，不填则返回最新交易日"),
    tag: Optional[str] = Query(None, description="标签过滤，如 ST股 / 三连板"),
):
    service = _risk_stock_service()
    items = service.get_items(trade_date=trade_date, tag=tag)
    latest_date = service.get_latest_trade_date()
    effective_date = items[0]["trade_date"] if items else (trade_date or latest_date)
    return {
        "trade_date": effective_date,
        "count": len(items),
        "data_status": "ready" if items else ("pending" if not latest_date else "empty"),
        "message": (
            "风险股清单已更新。"
            if items
            else (
                "清单尚未生成，系统会在收盘后自动刷新。"
                if not latest_date
                else "当前交易日暂无符合条件的标的。"
            )
        ),
        "items": [_serialize_item(item) for item in items],
    }


@admin_router.post("/refresh-auto")
async def admin_refresh_risk_stocks_auto(
    trade_date: Optional[str] = Query(None, description="交易日 YYYYMMDD，不填则自动识别最近交易日"),
    _: dict = Depends(require_admin),
):
    return _risk_stock_service().refresh_daily(trade_date=trade_date, source="admin-auto")


@admin_router.post("/refresh")
async def admin_refresh_risk_stocks(
    request: RiskStockRefreshRequest,
    _: dict = Depends(require_admin),
):
    return _risk_stock_service().refresh_from_rows(
        trade_date=request.trade_date,
        rows=request.rows,
        source=request.source,
    )
