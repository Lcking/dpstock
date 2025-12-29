"""
Judgment API Router
Handles judgment snapshot creation and retrieval with anonymous user identity
"""
from fastapi import APIRouter, Request, Response, HTTPException, Cookie
from typing import Optional, List
import uuid
from datetime import datetime
from pydantic import BaseModel

from schemas.analysis_v1 import JudgmentSnapshot
from services.judgment_service import JudgmentService
from utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/v1", tags=["judgments"])

# Initialize service
judgment_service = JudgmentService()

# Cookie settings
COOKIE_NAME = "aguai_uid"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year


def get_or_create_user_id(request: Request, response: Response, aguai_uid: Optional[str] = Cookie(None)) -> str:
    """
    Get user ID from cookie or create new one
    
    Args:
        request: FastAPI request
        response: FastAPI response
        aguai_uid: User ID from cookie
        
    Returns:
        user_id: Anonymous user ID
    """
    if aguai_uid:
        return aguai_uid
    
    # Generate new user ID
    new_user_id = str(uuid.uuid4())
    
    # Set cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=new_user_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax"
    )
    
    logger.info(f"Created new anonymous user: {new_user_id}")
    return new_user_id


# Request/Response models
class CreateJudgmentRequest(BaseModel):
    """Request model for creating judgment"""
    snapshot: JudgmentSnapshot


class CreateJudgmentResponse(BaseModel):
    """Response model for created judgment"""
    judgment_id: str
    user_id: str
    created_at: str


@router.post("/judgments", response_model=CreateJudgmentResponse)
async def create_judgment(
    request: Request,
    response: Response,
    body: CreateJudgmentRequest,
    aguai_uid: Optional[str] = Cookie(None)
):
    """
    Save a judgment snapshot
    
    - Reads or creates anonymous user ID from cookie
    - Saves judgment snapshot to database
    - Returns judgment ID
    """
    try:
        # Get or create user ID
        user_id = get_or_create_user_id(request, response, aguai_uid)
        
        # Create judgment
        judgment_id = judgment_service.create_judgment(user_id, body.snapshot)
        
        return CreateJudgmentResponse(
            judgment_id=judgment_id,
            user_id=user_id,
            created_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to create judgment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create judgment: {str(e)}")


@router.get("/me/judgments")
async def get_my_judgments(
    request: Request,
    response: Response,
    limit: int = 50,
    aguai_uid: Optional[str] = Cookie(None)
):
    """
    Get user's judgment history with latest verification status
    
    - Requires aguai_uid cookie (creates if not exists)
    - Returns list of judgments with latest check status
    - Ordered by creation time (newest first)
    """
    try:
        # Get or create user ID
        user_id = get_or_create_user_id(request, response, aguai_uid)
        
        # Get user judgments
        judgments = judgment_service.get_user_judgments(user_id, limit)
        
        return {
            "user_id": user_id,
            "total": len(judgments),
            "judgments": judgments
        }
        
    except Exception as e:
        logger.error(f"Failed to get user judgments: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get judgments: {str(e)}")


@router.get("/judgments/{judgment_id}")
async def get_judgment_detail(judgment_id: str):
    """
    Get judgment detail with latest verification result
    
    - Returns full judgment snapshot
    - Includes latest verification check if exists
    - Public endpoint (no auth required)
    """
    try:
        judgment = judgment_service.get_judgment_detail(judgment_id)
        
        if not judgment:
            raise HTTPException(status_code=404, detail="Judgment not found")
        
        return judgment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get judgment detail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get judgment detail: {str(e)}")
