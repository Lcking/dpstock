"""
Notification preference and unsubscribe routes.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from services.notify_pref_service import NotifyPrefService
from services.risk_alert_email_service import verify_risk_alert_unsubscribe_token
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

notify_pref_service = NotifyPrefService()


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_risk_alert_email(token: str = Query(..., min_length=10)):
    user_id = verify_risk_alert_unsubscribe_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="退订链接无效或已过期")

    notify_pref_service.set_risk_alert_email(user_id, False)
    logger.info(f"[Notifications] user={user_id} unsubscribed risk alert email")

    return HTMLResponse(
        content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>已退订风险提醒 - Agu AI</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f5f5f5; margin:0; }
    .card { max-width: 520px; margin: 80px auto; background:#fff; border-radius: 12px; padding: 32px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
    h1 { margin: 0 0 12px; font-size: 22px; color: #111827; }
    p { margin: 0; color: #4b5563; line-height: 1.7; }
    a { color: #667eea; text-decoration: none; }
  </style>
</head>
<body>
  <div class="card">
    <h1>已退订风险提醒邮件</h1>
    <p>你不会再收到「自选命中风险股清单」的邮件摘要。站内提醒不受影响。</p>
    <p style="margin-top:16px;"><a href="/">返回 Agu AI 首页</a></p>
  </div>
</body>
</html>
        """,
        status_code=200,
    )
