"""
Journal API Routes
判断记录 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Request, Response, Cookie
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from services.journal import journal_service
from routes.judgments import get_actor, get_or_create_user_id
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/journal", tags=["journal"])


def get_journal_user(
    request: Request,
    response: Response,
    aguai_uid: Optional[str] = Cookie(None)
) -> str:
    """获取当前用户ID (支持 AnchorToken, Anonymous Header 和 Cookie)"""
    # 1. Check for actor (Anchor or Header-based Anonymous)
    actor = get_actor(request)
    if actor:
        logger.info(f"[Journal] User identified via actor: type={actor['type']}, id={actor['id'][:16]}...")

        # If anchor is present, proactively merge other identities into anchor
        if actor.get("type") == "anchor":
            anchor_id = actor["id"]
            header_anon = request.headers.get("X-Anonymous-Id")

            migrated_total = 0
            try:
                if header_anon and header_anon != anchor_id:
                    migrated_total += journal_service.migrate_user_records(header_anon, anchor_id)
                # Cookie-based anonymous ID (legacy / quota uid) may have journal data from older versions
                if aguai_uid and aguai_uid != anchor_id:
                    migrated_total += journal_service.migrate_user_records(aguai_uid, anchor_id)
            except Exception as e:
                logger.warning(f"[Journal] Migration skipped due to error: {e}")

            if migrated_total > 0:
                logger.info(f"[Journal] Auto-merged records into anchor: migrated={migrated_total}")

        # If anonymous but only one anchor exists, fall back to anchor when anonymous has no records
        if actor.get("type") == "anonymous":
            try:
                anchor_id = journal_service.get_single_anchor_id()
                if anchor_id:
                    anon_count = journal_service.get_records_count(actor["id"])
                    anchor_count = journal_service.get_records_count(anchor_id)
                    if anon_count == 0 and anchor_count > 0:
                        logger.info("[Journal] Fallback to single anchor for anonymous session")
                        return anchor_id
            except Exception as e:
                logger.warning(f"[Journal] Anchor fallback skipped: {e}")

        return actor['id']
    
    # 2. Fallback to Cookie-based Anonymous
    user_id = get_or_create_user_id(request, response, aguai_uid)
    logger.info(f"[Journal] User identified via cookie/fallback: id={user_id[:16] if user_id else 'None'}...")
    return user_id


class CreateRecordRequest(BaseModel):
    """创建判断记录请求"""
    ts_code: str
    selected_candidate: str = Field(..., pattern="^[ABC]$")
    selected_premises: List[str] = []
    selected_risk_checks: List[str] = []
    constraints: Dict[str, Any] = {}
    validation_period_days: int = Field(7, ge=1, le=30)


class ReviewRequest(BaseModel):
    """复盘请求"""
    notes: Optional[str] = Field(None, max_length=500)


@router.post("")
async def create_record(
    request: CreateRecordRequest,
    user_id: str = Depends(get_journal_user)
):
    """创建判断记录"""
    try:
        result = journal_service.create_record(
            user_id=user_id,
            ts_code=request.ts_code,
            selected_candidate=request.selected_candidate,
            selected_premises=request.selected_premises,
            selected_risk_checks=request.selected_risk_checks,
            constraints=request.constraints,
            validation_period_days=request.validation_period_days
        )
        return result
    except Exception as e:
        logger.error(f"Create record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_records(
    status: Optional[str] = Query(None, description="状态过滤: active/due/reviewed"),
    ts_code: Optional[str] = Query(None, description="股票代码过滤"),
    page: int = Query(1, ge=1),
    user_id: str = Depends(get_journal_user)
):
    """获取判断记录列表"""
    try:
        # 先更新到期记录的状态
        due_updated = journal_service.run_due_check()
        if due_updated > 0:
            logger.info(f"[Journal] Updated {due_updated} records to 'due' status")
        
        records = journal_service.get_records(
            user_id=user_id,
            status=status,
            ts_code=ts_code,
            page=page
        )
        return {"records": records, "page": page}
    except Exception as e:
        logger.error(f"List records error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/due-count")
async def get_due_count(user_id: str = Depends(get_journal_user)):
    """获取待复盘记录数量"""
    try:
        count = journal_service.get_due_count(user_id)
        return {"due_count": count}
    except Exception as e:
        logger.error(f"Get due count error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{record_id}")
async def get_record(
    record_id: str,
    user_id: str = Depends(get_journal_user)
):
    """获取单个判断记录"""
    try:
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
    user_id: str = Depends(get_journal_user)
):
    """复盘判断记录"""
    try:
        result = journal_service.review_record(
            record_id=record_id,
            user_id=user_id,
            notes=request.notes
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Review record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run_due_check")
async def run_due_check():
    """运行到期检查 (内部cron调用)"""
    try:
        updated = journal_service.run_due_check()
        return {"updated": updated}
    except Exception as e:
        logger.error(f"Due check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
