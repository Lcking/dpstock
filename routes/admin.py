"""
Admin API Routes - System Statistics and User Management
"""
from fastapi import APIRouter, Header, HTTPException, Depends
from typing import Dict, Any, List
from services.admin_service import AdminService
import os

router = APIRouter()
admin_service = AdminService()

# Simple protection - replace with real auth in future if needed
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "stock-admin-2026")

def verify_admin_token(x_admin_token: str = Header(None, alias="X-Admin-Token")):
    print(f"[Admin] Token check: received='{x_admin_token}', expected='{ADMIN_TOKEN}'")
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        print(f"[Admin] Token REJECTED - 403")
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Admin Token")
    print(f"[Admin] Token OK")
    return x_admin_token

@router.get("/api/admin/stats", dependencies=[Depends(verify_admin_token)])
async def get_stats():
    """Get system-wide statistics"""
    print("[Admin] /api/admin/stats called")
    result = admin_service.get_system_stats()
    print(f"[Admin] Stats result: {result}")
    return result

@router.get("/api/admin/users", dependencies=[Depends(verify_admin_token)])
async def get_users(limit: int = 50):
    """Get list of registered users"""
    print(f"[Admin] /api/admin/users called with limit={limit}")
    result = admin_service.get_registered_users(limit)
    print(f"[Admin] Users result count: {len(result)}")
    return result
