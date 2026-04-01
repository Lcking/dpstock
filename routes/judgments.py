"""
Judgment API Router
Handles judgment snapshot creation and retrieval with unified user identity.
"""
from fastapi import APIRouter, Request, Response, HTTPException, Cookie, Depends
from typing import Optional, List
import uuid
from datetime import datetime
from functools import lru_cache
from pydantic import BaseModel

from auth.dependencies import get_current_user, UserContext
from schemas.analysis_v1 import JudgmentSnapshot
from services.judgment_service import JudgmentService
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/v1", tags=["judgments"])


@lru_cache(maxsize=1)
def get_judgment_service() -> JudgmentService:
    """Lazy init to avoid DB side effects during module import."""
    return JudgmentService()


class CreateJudgmentRequest(BaseModel):
    snapshot: JudgmentSnapshot


class CreateJudgmentResponse(BaseModel):
    judgment_id: str
    user_id: str
    created_at: str


@router.post("/judgments", response_model=CreateJudgmentResponse)
async def create_judgment(
    body: CreateJudgmentRequest,
    force: bool = False,
    user: UserContext = Depends(get_current_user),
):
    try:
        owner_type = "anchor" if user.is_authenticated else "anonymous"
        owner_id = user.anchor_id if user.anchor_id else user.user_id

        if not force:
            duplicate = get_judgment_service().check_duplicate(
                owner_type=owner_type,
                owner_id=owner_id,
                stock_code=body.snapshot.stock_code,
                structure_type=body.snapshot.structure_type,
                snapshot_date=body.snapshot.snapshot_time,
            )
            if duplicate:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "检测到重复判断",
                        "duplicate_id": duplicate["judgment_id"],
                        "created_at": duplicate["created_at"],
                        "stock_code": duplicate["stock_code"],
                        "structure_type": duplicate["structure_type"],
                    },
                )

        judgment_id = get_judgment_service().create_judgment(owner_type, owner_id, body.snapshot)

        return CreateJudgmentResponse(
            judgment_id=judgment_id,
            user_id=owner_id,
            created_at=datetime.now().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create judgment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create judgment: {str(e)}")


@router.get("/me/judgments")
async def get_my_judgments(
    limit: int = 50,
    user: UserContext = Depends(get_current_user),
):
    try:
        owner_type = "anchor" if user.is_authenticated else "anonymous"
        owner_id = user.anchor_id if user.anchor_id else user.user_id

        verify_result = {"checked": 0, "updated": 0}
        try:
            verify_result = get_judgment_service().verify_pending_judgments(
                owner_type=owner_type,
                owner_id=owner_id,
                max_checks=20,
            )
            logger.info(f"Lazy verification for {owner_type}:{owner_id[:8]}... - {verify_result}")
        except Exception as e:
            logger.error(f"Lazy verification failed: {e}")

        judgments = get_judgment_service().get_user_judgments(owner_type, owner_id, limit)

        return {
            "user_id": owner_id,
            "owner_type": owner_type,
            "owner_id": owner_id,
            "total": len(judgments),
            "judgments": judgments,
            "verification_stats": verify_result,
        }

    except Exception as e:
        logger.error(f"Failed to get judgments: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get judgments: {str(e)}")


@router.get("/judgments/{judgment_id}")
async def get_judgment_detail(judgment_id: str):
    try:
        judgment = get_judgment_service().get_judgment_detail(judgment_id)
        if not judgment:
            raise HTTPException(status_code=404, detail="Judgment not found")
        return judgment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get judgment detail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get judgment detail: {str(e)}")


@router.delete("/judgments/{judgment_id}")
async def delete_judgment(
    judgment_id: str,
    user: UserContext = Depends(get_current_user),
):
    try:
        owner_type = "anchor" if user.is_authenticated else "anonymous"
        owner_id = user.anchor_id if user.anchor_id else user.user_id

        judgment = get_judgment_service().get_judgment_detail(judgment_id)
        if not judgment:
            raise HTTPException(status_code=404, detail="判断不存在")

        if judgment["owner_type"] != owner_type or judgment["owner_id"] != owner_id:
            raise HTTPException(status_code=403, detail="无权删除此判断")

        success = get_judgment_service().delete_judgment(judgment_id)
        if success:
            logger.info(f"Deleted judgment: {judgment_id} by {owner_type}:{owner_id[:8]}...")
            return {"success": True, "message": "删除成功"}
        else:
            raise HTTPException(status_code=500, detail="删除失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete judgment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
