"""
Notification preference and unsubscribe routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from auth.dependencies import UserContext, get_current_user
from services.journal import journal_service
from services.notify_pref_service import NotifyPrefService
from services.risk_alert_email_service import verify_risk_alert_unsubscribe_token
from services.journal_due_email_service import verify_journal_due_unsubscribe_token
from services.watchlist_risk_alert_service import WatchlistRiskAlertService
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

notify_pref_service = NotifyPrefService()
watchlist_risk_alert_service = WatchlistRiskAlertService()


@router.get("/inbox")
async def get_notification_inbox(user: UserContext = Depends(get_current_user)):
    user_id = user.user_id
    due_count = journal_service.get_due_count(user_id)
    due_preview = []
    if due_count > 0:
        due_preview = [
            {
                "id": record.get("id"),
                "ts_code": record.get("ts_code"),
                "candidate": record.get("candidate"),
                "validation_date": record.get("validation_date"),
            }
            for record in journal_service.get_records(
                user_id,
                status="due",
                page=1,
                page_size=5,
            )
        ]

    risk_alert_count = watchlist_risk_alert_service.get_unread_count(user_id)
    risk_preview = []
    if risk_alert_count > 0:
        alerts = watchlist_risk_alert_service.list_alerts(
            user_id,
            limit=5,
            unread_only=True,
        )
        risk_preview = [
            {
                "id": item.get("id"),
                "stock_code": item.get("stock_code") or item.get("ts_code"),
                "stock_name": item.get("stock_name"),
                "trade_date": item.get("trade_date"),
                "tags": item.get("tags") or [],
            }
            for item in alerts.get("items") or []
        ]

    return {
        "due_count": due_count,
        "risk_alert_count": risk_alert_count,
        "due_preview": due_preview,
        "risk_preview": risk_preview,
    }


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


@router.get("/unsubscribe-journal-due", response_class=HTMLResponse)
async def unsubscribe_journal_due_email(token: str = Query(..., min_length=10)):
    user_id = verify_journal_due_unsubscribe_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="退订链接无效或已过期")

    notify_pref_service.set_journal_due_email(user_id, False)
    logger.info(f"[Notifications] user={user_id} unsubscribed journal due email")

    return HTMLResponse(
        content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>已退订待复盘提醒 - Agu AI</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f5f5f5; margin:0; }
    .card { max-width: 520px; margin: 80px auto; background:#fff; border-radius: 12px; padding: 32px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
    h1 { margin: 0 0 12px; font-size: 22px; color: #111827; }
    p { margin: 0; color: #4b5563; line-height: 1.7; }
    a { color: #6366f1; text-decoration: none; }
  </style>
</head>
<body>
  <div class="card">
    <h1>已退订待复盘提醒邮件</h1>
    <p>你不会再收到「判断已到验证期」的邮件摘要。站内待复盘提醒不受影响。</p>
    <p style="margin-top:16px;"><a href="/me">返回用户中心</a></p>
  </div>
</body>
</html>
        """,
        status_code=200,
    )
