"""
Admin API — separate JWT from end-user auth.
All routes require Bearer admin token except POST /login.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth.admin_auth import (
    admin_login_configured,
    create_admin_token,
    decode_admin_token,
    require_admin,
    verify_admin_password,
    _rate_limit_ok,
)
from database.db_factory import DatabaseFactory
from services.analyze_slo_tracker import analyze_slo_tracker
from services.app_settings_service import PATCHABLE_KEYS, AppSettingsService, ai_effective_for_admin_display
from services.job_health_tracker import job_health_tracker
from services.llm_usage_service import llm_usage_service
from services.archive_service import ArchiveService
from services.journal import journal_service
from services.nav_links_service import NavLinksService
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/admin", tags=["admin"])


@lru_cache(maxsize=1)
def _archive_service() -> ArchiveService:
    return ArchiveService()


@lru_cache(maxsize=1)
def _settings_service() -> AppSettingsService:
    return AppSettingsService()


@lru_cache(maxsize=1)
def _nav_service() -> NavLinksService:
    return NavLinksService()
class AdminLoginBody(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)


class ArticlePatchBody(BaseModel):
    title: Optional[str] = None
    stock_code: Optional[str] = None
    stock_name: Optional[str] = None
    market_type: Optional[str] = None
    content: Optional[str] = None
    score: Optional[int] = None
    legacy_score: Optional[int] = None
    score_version: Optional[str] = None
    ai_score_json: Optional[str] = None
    publish_date: Optional[str] = None


class UserPatchBody(BaseModel):
    status: str = Field(..., description="active | disabled")


class NavLinkCreateBody(BaseModel):
    label: str
    href: str
    target: str = "_blank"
    rel: str = "noopener"
    sort_order: int = 0
    enabled: int = 1


class NavLinkPatchBody(BaseModel):
    label: Optional[str] = None
    href: Optional[str] = None
    target: Optional[str] = None
    rel: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[int] = None


@router.post("/login")
async def admin_login(request: Request, body: AdminLoginBody):
    if not admin_login_configured():
        raise HTTPException(status_code=503, detail="管理员未配置（缺少 ADMIN_USERNAME 与密码）")

    client = request.client.host if request.client else "unknown"
    if not _rate_limit_ok(client):
        raise HTTPException(status_code=429, detail="登录尝试过多，请稍后再试")

    expected_user = (os.getenv("ADMIN_USERNAME") or "").strip()
    if body.username.strip() != expected_user or not verify_admin_password(body.password):
        logger.warning(f"[Admin] failed login for user={body.username!r} from {client}")
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_admin_token()
    return {"access_token": token, "token_type": "bearer", "expires_in_hours": int(os.getenv("ADMIN_JWT_EXPIRE_HOURS", "8"))}


@router.get("/me")
async def admin_me(_: dict = Depends(require_admin)):
    return {"role": "admin", "ok": True}


@router.get("/settings")
async def admin_get_settings(_: dict = Depends(require_admin)):
    rows = _settings_service().list_all()
    effective = ai_effective_for_admin_display()
    return {
        "settings": rows,
        "effective": effective,
        "patchable_keys": sorted(PATCHABLE_KEYS),
    }


@router.patch("/settings")
async def admin_patch_settings(
    body: Dict[str, str] = Body(..., examples=[{"ai.api_url": "https://api.example.com/v1/chat/completions"}]),
    _: dict = Depends(require_admin),
):
    updates: Dict[str, str] = {}
    for k, v in body.items():
        if k not in PATCHABLE_KEYS:
            continue
        if v is None:
            continue
        s = str(v).strip()
        if s == "":
            continue
        updates[k] = s
    if not updates:
        raise HTTPException(status_code=400, detail="无有效字段（仅允许 ai.api_url / ai.api_model / ai.api_timeout）")
    if "ai.api_timeout" in updates:
        try:
            int(updates["ai.api_timeout"])
        except ValueError:
            raise HTTPException(status_code=400, detail="ai.api_timeout 必须是整数秒")
    try:
        _settings_service().patch_many(updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "updated": list(updates.keys())}


@router.get("/articles")
async def admin_list_articles(
    limit: int = 50,
    offset: int = 0,
    q: Optional[str] = None,
    _: dict = Depends(require_admin),
):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    items, total = await _archive_service().admin_list_articles_with_total(limit, offset, q)
    return {"articles": items, "total": total, "limit": limit, "offset": offset}


@router.get("/articles/{article_id}")
async def admin_get_article(article_id: int, _: dict = Depends(require_admin)):
    row = await _archive_service().get_article_by_id(article_id)
    if not row:
        raise HTTPException(status_code=404, detail="文章不存在")
    return dict(row)


@router.patch("/articles/{article_id}")
async def admin_patch_article(article_id: int, body: ArticlePatchBody, _: dict = Depends(require_admin)):
    patch = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not patch:
        raise HTTPException(status_code=400, detail="无更新字段")
    ok = await _archive_service().update_article_by_id(article_id, patch)
    if not ok:
        raise HTTPException(status_code=404, detail="文章不存在或未变更")
    return {"ok": True}


@router.delete("/articles/{article_id}")
async def admin_delete_article(article_id: int, _: dict = Depends(require_admin)):
    ok = await _archive_service().delete_article_by_id(article_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {"ok": True}


@router.get("/users")
async def admin_list_users(
    limit: int = 50,
    offset: int = 0,
    q: Optional[str] = None,
    email_verified: Optional[int] = None,
    has_email: Optional[int] = None,
    _: dict = Depends(require_admin),
):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    with DatabaseFactory.get_connection() as conn:
        cur = conn.cursor()
        where = ["1=1"]
        params: List[Any] = []
        if q:
            where.append("(user_id LIKE ? OR primary_email LIKE ? OR display_name LIKE ?)")
            pat = f"%{q.strip()}%"
            params.extend([pat, pat, pat])
        if email_verified is not None:
            where.append("email_verified = ?")
            params.append(email_verified)
        if has_email == 1:
            where.append("(primary_email IS NOT NULL AND TRIM(primary_email) != '')")
        wh = " AND ".join(where)
        cur.execute(
            f"""
            SELECT user_id, primary_email, email_verified, display_name, status,
                   profile_completed, is_public_analysis_enabled, created_at, last_active_at
            FROM users
            WHERE {wh}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        rows = [dict(r) for r in cur.fetchall()]
        cur.execute(f"SELECT COUNT(*) AS c FROM users WHERE {wh}", params)
        total = int(cur.fetchone()["c"])
    return {"users": rows, "total": total, "limit": limit, "offset": offset}


@router.patch("/users/{user_id}")
async def admin_patch_user(user_id: str, body: UserPatchBody, _: dict = Depends(require_admin)):
    if body.status not in ("active", "disabled"):
        raise HTTPException(status_code=400, detail="status 只能是 active 或 disabled")
    with DatabaseFactory.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET status = ? WHERE user_id = ?", (body.status, user_id))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="用户不存在")
    return {"ok": True}


@router.post("/journal/{record_id}/force-due")
async def admin_force_journal_due(record_id: str, _: dict = Depends(require_admin)):
    result = journal_service.force_due_record(record_id)
    if result.get("error") == "Record not found":
        raise HTTPException(status_code=404, detail="判断记录不存在")
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("reason", "无法强制到期该记录"))
    return result


@router.get("/invites/summary")
async def admin_invite_summary(_: dict = Depends(require_admin)):
    with DatabaseFactory.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM invite_codes")
        codes = int(cur.fetchone()["c"])
        cur.execute("SELECT COUNT(*) AS c FROM invite_acceptances")
        acceptances = int(cur.fetchone()["c"])
        cur.execute("SELECT COUNT(*) AS c FROM invite_rewards")
        rewards = int(cur.fetchone()["c"])
        cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM invite_acceptances a
            LEFT JOIN invite_rewards r
              ON r.inviter_id = a.inviter_id AND r.invitee_id = a.invitee_id
            WHERE r.id IS NULL
            """
        )
        pending_acceptances = int(cur.fetchone()["c"])
        cur.execute(
            """
            SELECT inviter_id, COUNT(*) AS invite_count
            FROM invite_rewards
            GROUP BY inviter_id
            ORDER BY invite_count DESC
            LIMIT 30
            """
        )
        top = [dict(r) for r in cur.fetchall()]
    acceptance_rate = round(acceptances / codes * 100, 2) if codes else 0.0
    reward_rate = round(rewards / acceptances * 100, 2) if acceptances else 0.0
    return {
        "invite_codes_total": codes,
        "invite_acceptances_total": acceptances,
        "invite_rewards_total": rewards,
        "pending_acceptances_total": pending_acceptances,
        "acceptance_rate": acceptance_rate,
        "reward_rate": reward_rate,
        "top_inviters": top,
    }


@router.get("/invites/acceptances")
async def admin_invite_acceptances(limit: int = 100, offset: int = 0, _: dict = Depends(require_admin)):
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    with DatabaseFactory.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                a.id,
                a.inviter_id,
                a.invitee_id,
                a.invite_code,
                a.accepted_at,
                COALESCE(ar.analysis_count, 0) AS analysis_count,
                CASE
                    WHEN r.id IS NOT NULL THEN 'rewarded'
                    WHEN COALESCE(ar.analysis_count, 0) > 0 THEN 'analysis_without_reward'
                    ELSE 'pending_first_analysis'
                END AS status,
                r.reward_quota,
                r.reward_date,
                r.created_at AS rewarded_at
            FROM invite_acceptances a
            LEFT JOIN (
                SELECT user_id, COUNT(*) AS analysis_count
                FROM analysis_records
                GROUP BY user_id
            ) ar ON ar.user_id = a.invitee_id
            LEFT JOIN invite_rewards r
              ON r.inviter_id = a.inviter_id AND r.invitee_id = a.invitee_id
            ORDER BY a.accepted_at DESC, a.id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = [dict(r) for r in cur.fetchall()]

    pending_count = sum(1 for row in rows if row.get("status") == "pending_first_analysis")
    rewarded_count = sum(1 for row in rows if row.get("status") == "rewarded")
    return {
        "acceptances": rows,
        "pending_count": pending_count,
        "rewarded_count": rewarded_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/invites/diagnose/{invitee_id}")
async def admin_invite_diagnosis(invitee_id: str, _: dict = Depends(require_admin)):
    with DatabaseFactory.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, inviter_id, invitee_id, invite_code, accepted_at
            FROM invite_acceptances
            WHERE invitee_id = ?
            ORDER BY accepted_at DESC, id DESC
            LIMIT 1
            """,
            (invitee_id,),
        )
        acceptance = cur.fetchone()

        cur.execute(
            """
            SELECT COUNT(*) AS c, GROUP_CONCAT(stock_code) AS stocks
            FROM analysis_records
            WHERE user_id = ?
            """,
            (invitee_id,),
        )
        analysis_row = cur.fetchone()
        analysis_count = int(analysis_row["c"]) if analysis_row else 0
        analyzed_stocks = []
        if analysis_row and analysis_row["stocks"]:
            analyzed_stocks = str(analysis_row["stocks"]).split(",")

        reward = None
        if acceptance:
            cur.execute(
                """
                SELECT id, inviter_id, invitee_id, invite_code, reward_quota, reward_date, created_at
                FROM invite_rewards
                WHERE inviter_id = ? AND invitee_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (acceptance["inviter_id"], invitee_id),
            )
            reward_row = cur.fetchone()
            reward = dict(reward_row) if reward_row else None

    if not acceptance:
        return {
            "invitee_id": invitee_id,
            "status": "no_acceptance",
            "acceptance": None,
            "analysis_count": analysis_count,
            "analyzed_stocks": analyzed_stocks,
            "reward": None,
            "reason": "没有找到接受邀请记录，可能不是通过有效邀请链接进入。",
            "next_action": "确认用户是否使用了正确邀请链接，或让用户重新打开邀请链接。",
        }

    acceptance_dict = dict(acceptance)
    if reward:
        status = "rewarded"
        reason = "奖励已经发放。"
        next_action = "无需处理；如用户仍反馈异常，请核对邀请人与用户身份是否一致。"
    elif analysis_count == 0:
        status = "pending_first_analysis"
        reason = "被邀请者还没有完成首次分析，所以奖励尚未发放。"
        next_action = "引导被邀请者完成首次分析。"
    else:
        status = "analysis_without_reward"
        reason = "被邀请者已有分析记录，但没有匹配到奖励记录。"
        next_action = "检查分析是否发生在接受邀请之后，以及日志中是否有发奖失败。"

    return {
        "invitee_id": invitee_id,
        "status": status,
        "acceptance": acceptance_dict,
        "analysis_count": analysis_count,
        "analyzed_stocks": analyzed_stocks,
        "reward": reward,
        "reason": reason,
        "next_action": next_action,
    }


@router.get("/invites/rewards")
async def admin_invite_rewards(limit: int = 100, offset: int = 0, _: dict = Depends(require_admin)):
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    with DatabaseFactory.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, inviter_id, invitee_id, invite_code, reward_quota, reward_date, created_at
            FROM invite_rewards
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = [dict(r) for r in cur.fetchall()]
    return {"rewards": rows, "limit": limit, "offset": offset}


@router.get("/nav-links")
async def admin_nav_list(_: dict = Depends(require_admin)):
    return {"links": _nav_service().list_all()}


@router.post("/nav-links")
async def admin_nav_create(body: NavLinkCreateBody, _: dict = Depends(require_admin)):
    new_id = _nav_service().create(
        label=body.label,
        href=body.href,
        target=body.target,
        rel=body.rel,
        sort_order=body.sort_order,
        enabled=body.enabled,
    )
    return {"id": new_id}


@router.patch("/nav-links/{link_id}")
async def admin_nav_patch(link_id: int, body: NavLinkPatchBody, _: dict = Depends(require_admin)):
    patch = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not patch:
        raise HTTPException(status_code=400, detail="无更新字段")
    ok = _nav_service().update(link_id, patch)
    if not ok:
        raise HTTPException(status_code=404, detail="链接不存在或未变更")
    return {"ok": True}


@router.delete("/nav-links/{link_id}")
async def admin_nav_delete(link_id: int, _: dict = Depends(require_admin)):
    ok = _nav_service().delete(link_id)
    if not ok:
        raise HTTPException(status_code=404, detail="链接不存在")
    return {"ok": True}


@router.get("/ops/summary")
async def admin_ops_summary(days: int = 7, _: dict = Depends(require_admin)):
    """Ops dashboard: analyze SLO, scheduler health, LLM usage rollup."""
    days = max(1, min(int(days), 90))
    slo = analyze_slo_tracker.snapshot()
    return {
        "analyze_slo": {
            **slo,
            "scope": "since_process_restart",
            "note": "内存统计，容器重启后清零；下方「分析用量」来自数据库历史记录。",
        },
        "job_health": job_health_tracker.snapshot(),
        "llm_usage": llm_usage_service.get_summary(days=days),
    }


@router.get("/ops/llm-usage")
async def admin_ops_llm_usage(days: int = 7, _: dict = Depends(require_admin)):
    days = max(1, min(int(days), 90))
    return llm_usage_service.get_summary(days=days)
