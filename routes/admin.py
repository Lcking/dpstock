"""
Admin API Routes - System Statistics and User Management
"""
from fastapi import APIRouter, Header, HTTPException, Depends
from services.admin_service import AdminService
import os
from functools import lru_cache
from utils.logger import get_logger

router = APIRouter()
logger = get_logger()


@lru_cache(maxsize=1)
def get_admin_service() -> AdminService:
    return AdminService()

# Explicit-only protection. Do not ship a hardcoded fallback token.
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()

def verify_admin_token(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    if not ADMIN_TOKEN:
        logger.warning("[Admin] Route accessed but ADMIN_TOKEN is not configured")
        raise HTTPException(status_code=403, detail="Forbidden")
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Admin Token")
    return x_admin_token

@router.get("/api/admin/stats", dependencies=[Depends(verify_admin_token)])
async def get_stats():
    """Get system-wide statistics"""
    return get_admin_service().get_system_stats()

@router.get("/api/admin/users", dependencies=[Depends(verify_admin_token)])
async def get_users(limit: int = 50):
    """Get list of registered users"""
    return get_admin_service().get_registered_users(limit)
