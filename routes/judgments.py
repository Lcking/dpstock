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
        # Verify anchor token
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
    
    # Fallback: return None (will use cookie-based ID)
    return None


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
    force: bool = False,
    aguai_uid: Optional[str] = Cookie(None)
):
    """
    Save a judgment snapshot
    
    - Supports both anonymous (cookie/header) and anchor (token) users
    - Saves judgment snapshot to database with owner info
    - Returns judgment ID
    """
    try:
        # Get actor (anchor or anonymous)
        actor = get_actor(request)
        
        if actor:
            # Use actor from token or header
            owner_type = actor['type']
            owner_id = actor['id']
        else:
            # Fallback to cookie-based anonymous
            user_id = get_or_create_user_id(request, response, aguai_uid)
            owner_type = 'anonymous'
            owner_id = user_id
        
        # Check for duplicates (unless force flag is set)
        if not force:
            duplicate = judgment_service.check_duplicate(
                owner_type=owner_type,
                owner_id=owner_id,
                stock_code=body.snapshot.stock_code,
                structure_type=body.snapshot.structure_type,
                snapshot_date=body.snapshot.snapshot_time
            )
            
            if duplicate:
                # Return 409 Conflict with duplicate info
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "检测到重复判断",
                        "duplicate_id": duplicate['judgment_id'],
                        "created_at": duplicate['created_at'],
                        "stock_code": duplicate['stock_code'],
                        "structure_type": duplicate['structure_type']
                    }
                )
        
        # Create judgment with owner info
        judgment_id = judgment_service.create_judgment(owner_type, owner_id, body.snapshot)
        
        return CreateJudgmentResponse(
            judgment_id=judgment_id,
            user_id=owner_id,  # For backward compatibility
            created_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
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
    
    - Supports both anonymous (cookie/header) and anchor (token) users
    - Returns list of judgments with latest check status
    - Ordered by creation time (newest first)
    """
    try:
        # Get actor (anchor or anonymous)
        actor = get_actor(request)
        
        if actor:
            # Use actor from token or header
            owner_type = actor['type']
            owner_id = actor['id']
        else:
            # Fallback to cookie-based anonymous
            user_id = get_or_create_user_id(request, response, aguai_uid)
            owner_type = 'anonymous'
            owner_id = user_id
        
        
        # LAZY VERIFICATION TRIGGER (V1)
        # Automatically verify pending judgments when user opens page
        verify_result = {"checked": 0, "updated": 0}
        try:
            verify_result = judgment_service.verify_pending_judgments(
                owner_type=owner_type,
                owner_id=owner_id,
                max_checks=20  # Limit to prevent timeout
            )
            logger.info(f"Lazy verification for {owner_type}:{owner_id[:8]}... - {verify_result}")
        except Exception as e:
            logger.error(f"Lazy verification failed: {e}")
            # Don't fail the request if verification fails
        
        # Get judgments (now with updated verification status)
        judgments = judgment_service.get_user_judgments(owner_type, owner_id, limit)
        
        return {
            "user_id": owner_id,  # For backward compatibility
            "owner_type": owner_type,
            "owner_id": owner_id,
            "total": len(judgments),
            "judgments": judgments,
            "verification_stats": verify_result  # Optional: show verification stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get judgments: {str(e)}")
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


@router.delete("/judgments/{judgment_id}")
async def delete_judgment(
    judgment_id: str,
    request: Request
):
    """
    Delete a judgment (hard delete)
    
    Authorization:
    - Owner (anchor or anonymous) can delete their own judgments
    - Returns 403 if not owner
    - Returns 404 if judgment not found
    """
    try:
        # Get actor (anchor or anonymous)
        actor = get_actor(request)
        
        if not actor:
            raise HTTPException(status_code=401, detail="未授权")
        
        # Get judgment to verify ownership
        judgment = judgment_service.get_judgment_detail(judgment_id)
        
        if not judgment:
            raise HTTPException(status_code=404, detail="判断不存在")
        
        # Verify ownership
        if judgment['owner_type'] != actor['type'] or judgment['owner_id'] != actor['id']:
            raise HTTPException(status_code=403, detail="无权删除此判断")
        
        # Delete
        success = judgment_service.delete_judgment(judgment_id)
        
        if success:
            logger.info(f"Deleted judgment: {judgment_id} by {actor['type']}:{actor['id'][:8]}...")
            return {"success": True, "message": "删除成功"}
        else:
            raise HTTPException(status_code=500, detail="删除失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete judgment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
