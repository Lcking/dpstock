"""
Anchor API Routes - Email Binding and Verification
Endpoints:
- POST /api/anchor/send_code - Send verification code to email
- POST /api/anchor/verify_and_bind - Verify code and bind email to anonymous ID
- GET /api/anchor/status - Get current anchor status
"""

from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import re
from services.anchor_service import AnchorService
from utils.logger import get_logger

logger = get_logger()

router = APIRouter()

# Initialize anchor service
DB_PATH = os.getenv('DB_PATH', 'data/stock_scanner.db')
JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
anchor_service = AnchorService(DB_PATH, JWT_SECRET)

# ============ Request/Response Models ============

class SendCodeRequest(BaseModel):
    email: EmailStr

class SendCodeResponse(BaseModel):
    ok: bool
    message: str

class VerifyAndBindRequest(BaseModel):
    email: EmailStr
    code: str

class VerifyAndBindResponse(BaseModel):
    anchor_id: str
    token: str
    migrated_count: int
    masked_email: str

class AnchorStatusResponse(BaseModel):
    mode: str  # 'anonymous' or 'anchor'
    masked_email: Optional[str] = None

# ============ Helper Functions ============

def get_actor(request: Request) -> dict:
    """
    Extract actor identity from request
    Priority: 1. Bearer token -> 2. X-Anonymous-Id header
    Returns: {'type': 'anchor'|'anonymous', 'id': str}
    """
    # Check Authorization header for anchor token
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '')
        anchor_id = anchor_service.verify_anchor_token(token)
        if anchor_id:
            return {'type': 'anchor', 'id': anchor_id}
    
    # Check X-Anonymous-Id header
    anonymous_id = request.headers.get('X-Anonymous-Id')
    if anonymous_id:
        return {'type': 'anonymous', 'id': anonymous_id}
    
    # Fallback: generate temporary (frontend should always provide)
    import uuid
    temp_id = str(uuid.uuid4())
    logger.warning(f"请求缺少身份标识,生成临时ID: {temp_id}")
    return {'type': 'anonymous', 'id': temp_id}

def validate_email_format(email: str) -> bool:
    """Basic email format validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ============ API Endpoints ============

@router.post("/api/anchor/send_code", response_model=SendCodeResponse)
async def send_verification_code(request: SendCodeRequest):
    """
    Send verification code to email
    
    Rate limits:
    - Max 1 send per 60 seconds
    - Max 10 sends per day
    """
    email = request.email.lower().strip()
    
    # Validate email format
    if not validate_email_format(email):
        raise HTTPException(status_code=400, detail="邮箱格式无效")
    
    email_hash = anchor_service.hash_email(email)
    email_masked = anchor_service.mask_email(email)
    
    # Check rate limit
    allowed, error_msg = anchor_service.check_send_code_rate_limit(email_hash)
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)
    
    # Generate and save code
    code = anchor_service.generate_code()
    anchor_service.save_verification_code(email_hash, code)
    
    # V-1: Print to console (no email service yet)
    logger.info(f"=== 验证码 ===")
    logger.info(f"邮箱: {email_masked}")
    logger.info(f"验证码: {code}")
    logger.info(f"有效期: 10分钟")
    logger.info(f"=============")
    
    # TODO V-2: Send actual email via SendGrid/Resend
    # await send_email(email, code)
    
    return SendCodeResponse(
        ok=True,
        message=f"验证码已发送到 {email_masked} (开发环境:请查看服务器日志)"
    )

@router.post("/api/anchor/verify_and_bind", response_model=VerifyAndBindResponse)
async def verify_and_bind(
    request: VerifyAndBindRequest,
    x_anonymous_id: Optional[str] = Header(None, alias="X-Anonymous-Id")
):
    """
    Verify email code and bind to anonymous ID
    Migrates all anonymous judgments to anchor
    
    Requires X-Anonymous-Id header
    """
    if not x_anonymous_id:
        raise HTTPException(
            status_code=400, 
            detail="缺少 X-Anonymous-Id header,无法绑定"
        )
    
    email = request.email.lower().strip()
    code = request.code.strip()
    
    # Validate code format (6 digits)
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=400, detail="验证码格式错误")
    
    email_hash = anchor_service.hash_email(email)
    
    # Verify code
    valid, error_msg = anchor_service.verify_code(email_hash, code)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Get or create anchor
    anchor_id = anchor_service.get_or_create_anchor(email)
    
    # Migrate anonymous judgments to anchor
    migrated_count = anchor_service.migrate_anonymous_to_anchor(
        anonymous_id=x_anonymous_id,
        anchor_id=anchor_id
    )
    
    # Generate token
    token = anchor_service.generate_anchor_token(anchor_id)
    
    # Get masked email
    masked_email = anchor_service.mask_email(email)
    
    logger.info(f"绑定成功: anonymous={x_anonymous_id} -> anchor={anchor_id}, migrated={migrated_count}")
    
    return VerifyAndBindResponse(
        anchor_id=anchor_id,
        token=token,
        migrated_count=migrated_count,
        masked_email=masked_email
    )

@router.get("/api/anchor/status", response_model=AnchorStatusResponse)
async def get_anchor_status(request: Request):
    """
    Get current anchor binding status
    Returns mode and masked email if bound
    """
    actor = get_actor(request)
    
    if actor['type'] == 'anchor':
        # Get anchor info
        anchor = anchor_service.get_anchor_by_id(actor['id'])
        if anchor:
            return AnchorStatusResponse(
                mode='anchor',
                masked_email=anchor.get('anchor_value_masked')
            )
    
    return AnchorStatusResponse(mode='anonymous')

# ============ Cleanup Task (Optional) ============

@router.post("/api/anchor/cleanup")
async def cleanup_expired_codes():
    """
    Admin endpoint: Clean up expired verification codes
    Should be called periodically (e.g., daily cron job)
    """
    deleted_count = anchor_service.cleanup_expired_codes()
    return {"ok": True, "deleted_count": deleted_count}
