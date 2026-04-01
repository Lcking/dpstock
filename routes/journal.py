"""
Journal API Routes — uses unified auth
判断记录 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from auth.dependencies import get_current_user, UserContext
from services.journal import journal_service
from services.user_service import UserService
from utils.logger import get_logger

logger = get_logger()
user_service = UserService()

router = APIRouter(prefix="/api/journal", tags=["journal"])


def _resolve_journal_user(user: UserContext) -> str:
    """
    Return the canonical user_id for journal operations.

    Special case: when the request is anonymous and there is exactly one
    anchor in the system with journal records (but the anonymous id has
    none), fall back to that anchor's user — preserves the old single-user
    demo behaviour.
    """
    if user.is_authenticated:
        return user.user_id

    try:
        single_anchor_id = journal_service.get_single_anchor_id()
        if single_anchor_id:
            anchor_user_id = user_service.resolve_request_user(anchor_id=single_anchor_id)["user_id"]
            anon_count = journal_service.get_records_count(user.user_id)
            anchor_count = journal_service.get_records_count(anchor_user_id)
            if anon_count == 0 and anchor_count > 0:
                logger.info("[Journal] Fallback to single anchor for anonymous session")
                return anchor_user_id
    except Exception as e:
        logger.warning(f"[Journal] Anchor fallback skipped: {e}")

    return user.user_id


class CreateRecordRequest(BaseModel):
    ts_code: str
    selected_candidate: str = Field(..., pattern="^[ABC]$")
    selected_premises: List[str] = []
    selected_risk_checks: List[str] = []
    constraints: Dict[str, Any] = {}
    validation_period_days: int = Field(7, ge=1, le=30)


class ReviewRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=500)


@router.post("")
async def create_record(
    request: CreateRecordRequest,
    user: UserContext = Depends(get_current_user),
):
    try:
        user_id = _resolve_journal_user(user)
        return journal_service.create_record(
            user_id=user_id,
            ts_code=request.ts_code,
            selected_candidate=request.selected_candidate,
            selected_premises=request.selected_premises,
            selected_risk_checks=request.selected_risk_checks,
            constraints=request.constraints,
            validation_period_days=request.validation_period_days,
        )
    except Exception as e:
        logger.error(f"Create record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_records(
    status: Optional[str] = Query(None, description="状态过滤: active/due/reviewed"),
    ts_code: Optional[str] = Query(None, description="股票代码过滤"),
    page: int = Query(1, ge=1),
    user: UserContext = Depends(get_current_user),
):
    try:
        user_id = _resolve_journal_user(user)
        due_updated = journal_service.run_due_check()
        if due_updated > 0:
            logger.info(f"[Journal] Updated {due_updated} records to 'due' status")

        records = journal_service.get_records(
            user_id=user_id,
            status=status,
            ts_code=ts_code,
            page=page,
        )
        return {
            "records": records,
            "page": page,
            **journal_service.get_journal_state(user_id),
        }
    except Exception as e:
        logger.error(f"List records error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/due-count")
async def get_due_count(user: UserContext = Depends(get_current_user)):
    try:
        user_id = _resolve_journal_user(user)
        return {"due_count": journal_service.get_due_count(user_id)}
    except Exception as e:
        logger.error(f"Get due count error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{record_id}")
async def get_record(
    record_id: str,
    user: UserContext = Depends(get_current_user),
):
    try:
        user_id = _resolve_journal_user(user)
        records = journal_service.get_records(user_id=user_id)
        for r in records:
            if r.get("id") == record_id:
                return r
        raise HTTPException(status_code=404, detail="Record not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{record_id}/review")
async def review_record(
    record_id: str,
    request: ReviewRequest,
    user: UserContext = Depends(get_current_user),
):
    try:
        user_id = _resolve_journal_user(user)
        result = journal_service.review_record(
            record_id=record_id,
            user_id=user_id,
            notes=request.notes,
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Review record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{record_id}")
async def delete_record(
    record_id: str,
    user: UserContext = Depends(get_current_user),
):
    try:
        user_id = _resolve_journal_user(user)
        ok = journal_service.delete_record(record_id=record_id, user_id=user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Record not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run_due_check")
async def run_due_check():
    try:
        updated = journal_service.run_due_check()
        return {"updated": updated}
    except Exception as e:
        logger.error(f"Due check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
