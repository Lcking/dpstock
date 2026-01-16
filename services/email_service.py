"""
Email Service - Send verification codes via Resend
Simple and reliable email delivery for anchor system
"""

import os
import resend
from typing import Optional
from utils.logger import get_logger

logger = get_logger()

# Initialize Resend API key from environment
RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')
SEND_REAL_EMAIL = os.getenv('SEND_REAL_EMAIL', 'false').lower() == 'true'
FROM_EMAIL = os.getenv('FROM_EMAIL', 'Aguai <noreply@aguai.net>')

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    logger.info("Resend email service initialized")
else:
    logger.warning("RESEND_API_KEY not set, emails will only be logged")


def send_verification_code(email: str, code: str, masked_email: str) -> tuple[bool, str]:
    """
    Send verification code email to user
    
    Args:
        email: User's email address
        code: 6-digit verification code
        masked_email: Masked email for logging (e.g., u***@example.com)
        
    Returns:
        (success: bool, message: str)
    """
    
    # If SEND_REAL_EMAIL is disabled, just log
    if not SEND_REAL_EMAIL or not RESEND_API_KEY:
        logger.info("=== 验证码 (开发模式) ===")
        logger.info(f"邮箱: {masked_email}")
        logger.info(f"验证码: {code}")
        logger.info(f"有效期: 10分钟")
        logger.info("=" * 30)
        return True, f"验证码已发送到 {masked_email} (开发环境:请查看服务器日志)"
    
    # Send real email via Resend
    try:
        params = {
            "from": FROM_EMAIL,
            "to": [email],
            "subject": "Aguai 验证码",
            "html": f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f5f5f5;">
    <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px; text-align: center; border-radius: 8px 8px 0 0;">
            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">Aguai 验证码</h1>
        </div>
        
        <!-- Content -->
        <div style="padding: 40px 32px;">
            <p style="margin: 0 0 24px 0; color: #333333; font-size: 16px; line-height: 1.6;">
                您好,
            </p>
            
            <p style="margin: 0 0 24px 0; color: #333333; font-size: 16px; line-height: 1.6;">
                您正在绑定邮箱到 Aguai 判断系统。您的验证码是:
            </p>
            
            <!-- Verification Code -->
            <div style="background-color: #f8f9fa; border: 2px dashed #667eea; border-radius: 8px; padding: 24px; text-align: center; margin: 32px 0;">
                <div style="font-size: 36px; font-weight: 700; color: #667eea; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                    {code}
                </div>
            </div>
            
            <p style="margin: 24px 0; color: #666666; font-size: 14px; line-height: 1.6;">
                ⏱️ 验证码有效期为 <strong>10分钟</strong>
            </p>
            
            <p style="margin: 24px 0; color: #666666; font-size: 14px; line-height: 1.6;">
                如果这不是您的操作,请忽略此邮件。
            </p>
        </div>
        
        <!-- Footer -->
        <div style="background-color: #f8f9fa; padding: 24px 32px; border-radius: 0 0 8px 8px; border-top: 1px solid #e9ecef;">
            <p style="margin: 0; color: #999999; font-size: 12px; text-align: center; line-height: 1.6;">
                此邮件由 Aguai 自动发送,请勿回复<br/>
                © 2026 Aguai - 智能股票分析平台
            </p>
        </div>
    </div>
</body>
</html>
            """
        }
        
        response = resend.Emails.send(params)
        
        logger.info(f"验证码邮件已发送到 {masked_email}, Resend ID: {response.get('id', 'N/A')}")
        return True, f"验证码已发送到 {masked_email},请查收邮件"
        
    except Exception as e:
        logger.error(f"发送验证码邮件失败 ({masked_email}): {str(e)}")
        
        # Fallback to logging if email fails
        logger.info("=== 验证码 (邮件发送失败,回退到日志) ===")
        logger.info(f"邮箱: {masked_email}")
        logger.info(f"验证码: {code}")
        logger.info("=" * 40)
        
        return False, "邮件发送失败,请稍后重试或联系管理员"


def test_email_service() -> bool:
    """
    Test email service configuration
    Returns True if service is properly configured
    """
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured")
        return False
    
    if not SEND_REAL_EMAIL:
        logger.info("SEND_REAL_EMAIL is disabled, using log-only mode")
        return True
    
    logger.info("Email service is properly configured")
    return True
