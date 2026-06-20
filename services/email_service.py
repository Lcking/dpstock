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


def _format_trade_date_label(trade_date: str) -> str:
    raw = str(trade_date or "").strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


def _render_alert_rows(alerts: list) -> str:
    rows = []
    for item in alerts:
        name = str(item.get("stock_name") or item.get("ts_code") or "").strip()
        ts_code = str(item.get("ts_code") or "").strip()
        tags = item.get("tags") or []
        tag_text = "、".join(str(tag) for tag in tags[:4]) or "风险标的"
        reason = str(item.get("reason") or "").strip() or "已进入当日风险股清单"
        rows.append(
            f"""
            <tr>
                <td style="padding: 12px 0; border-bottom: 1px solid #eef0f4;">
                    <div style="font-size: 15px; font-weight: 600; color: #1f2937;">{name}</div>
                    <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">{ts_code}</div>
                </td>
                <td style="padding: 12px 0; border-bottom: 1px solid #eef0f4; color: #b45309; font-size: 13px;">{tag_text}</td>
                <td style="padding: 12px 0; border-bottom: 1px solid #eef0f4; color: #4b5563; font-size: 13px;">{reason}</td>
            </tr>
            """
        )
    return "".join(rows)


def send_risk_alert_digest(
    email: str,
    trade_date: str,
    alerts: list,
    *,
    unsubscribe_url: str,
    site_base_url: str = "https://aguai.net",
) -> tuple[bool, str]:
    """
    Send a daily digest when watchlist symbols hit the risk stock list.
    """
    masked = email
    if "@" in email:
        local, domain = email.split("@", 1)
        masked = f"{local[0]}***@{domain}" if local else email

    date_label = _format_trade_date_label(trade_date)
    count = len(alerts or [])
    alert_rows = _render_alert_rows(alerts or [])
    risk_list_url = f"{site_base_url.rstrip('/')}/risk-stocks"
    watchlist_url = f"{site_base_url.rstrip('/')}/"

    if not SEND_REAL_EMAIL or not RESEND_API_KEY:
        logger.info("=== 风险提醒邮件 (开发模式) ===")
        logger.info(f"邮箱: {masked}")
        logger.info(f"交易日: {date_label}")
        logger.info(f"命中数量: {count}")
        for item in alerts or []:
            logger.info(
                f"- {item.get('stock_name')} ({item.get('ts_code')}): "
                f"{', '.join(item.get('tags') or [])}"
            )
        logger.info(f"退订链接: {unsubscribe_url}")
        logger.info("=" * 40)
        return True, f"风险提醒摘要已记录到日志 ({masked})"

    try:
        params = {
            "from": FROM_EMAIL,
            "to": [email],
            "subject": f"Aguai 自选风险提醒 · {date_label}（{count} 只命中）",
            "html": f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.08);overflow:hidden;">
    <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:28px 24px;color:#fff;">
      <h1 style="margin:0;font-size:22px;">自选风险提醒</h1>
      <p style="margin:10px 0 0;font-size:14px;opacity:0.92;">{date_label} 有 {count} 只自选标的进入当日风险股清单</p>
    </div>
    <div style="padding:24px;">
      <p style="margin:0 0 16px;color:#374151;font-size:15px;line-height:1.7;">
        以下标的出现在 Aguai 每日风险股清单中，仅供风险识别与研究参考，不构成投资建议。
      </p>
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr>
            <th align="left" style="font-size:12px;color:#6b7280;padding-bottom:8px;">标的</th>
            <th align="left" style="font-size:12px;color:#6b7280;padding-bottom:8px;">标签</th>
            <th align="left" style="font-size:12px;color:#6b7280;padding-bottom:8px;">原因</th>
          </tr>
        </thead>
        <tbody>{alert_rows}</tbody>
      </table>
      <div style="margin-top:24px;">
        <a href="{risk_list_url}" style="display:inline-block;background:#667eea;color:#fff;text-decoration:none;padding:10px 16px;border-radius:8px;font-size:14px;">查看完整风险股清单</a>
        <a href="{watchlist_url}" style="display:inline-block;margin-left:8px;color:#667eea;text-decoration:none;font-size:14px;">回到诊股首页</a>
      </div>
      <p style="margin:24px 0 0;color:#9ca3af;font-size:12px;line-height:1.7;">
        免责声明：本邮件基于公开行情与规则化筛选自动生成，仅供参考，不构成任何投资建议。股市有风险，入市需谨慎。
      </p>
    </div>
    <div style="background:#f8f9fa;padding:18px 24px;border-top:1px solid #e9ecef;">
      <p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;text-align:center;">
        不想再收到此类邮件？<a href="{unsubscribe_url}" style="color:#667eea;">点此退订风险提醒</a><br/>
        © 2026 Aguai - 智能股票分析平台
      </p>
    </div>
  </div>
</body>
</html>
            """,
        }
        response = resend.Emails.send(params)
        logger.info(
            f"风险提醒邮件已发送到 {masked}, items={count}, Resend ID: {response.get('id', 'N/A')}"
        )
        return True, f"风险提醒摘要已发送到 {masked}"
    except Exception as exc:
        logger.error(f"发送风险提醒邮件失败 ({masked}): {exc}")
        return False, str(exc)
