from fastapi import APIRouter, Header, HTTPException, Depends
from typing import Dict, Any, List
from services.admin_service import AdminService
import os

router = APIRouter()
admin_service = AdminService()

# Simple protection - replace with real auth in future if needed
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "stock-admin-2026")

def verify_admin_token(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Admin Token")
    return x_admin_token

@router.get("/api/admin/stats", dependencies=[Depends(verify_admin_token)])
async def get_stats():
    """Get system-wide statistics"""
    return admin_service.get_system_stats()

@router.get("/api/admin/users", dependencies=[Depends(verify_admin_token)])
async def get_users(limit: int = 50):
    """Get list of registered users"""
    return admin_service.get_registered_users(limit)
