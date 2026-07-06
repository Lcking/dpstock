"""
Weekly judgment recap SSR page — aggregates verifier outcomes for GEO/trust surfaces.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.db_factory import DatabaseFactory
from services.journal.condition_quality import extract_selected_condition_description
from services.judgment_accuracy_service import JudgmentAccuracyService
from utils.logger import get_logger

logger = get_logger()


class JudgmentRecapService:
    def __init__(self, base_url: str = "https://aguai.net", db_path: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        if db_path:
            DatabaseFactory.initialize(db_path)
        self.db_path = db_path or DatabaseFactory.get_db_path()
        self.db = DatabaseFactory
        self.accuracy_service = JudgmentAccuracyService()

    def get_weekly_recap_payload(self, window_days: int = 7) -> Dict[str, Any]:
        window_days = min(max(int(window_days or 7), 7), 30)
        stats = self.accuracy_service.get_public_accuracy_stats(window_days=window_days)
        cases = self._fetch_highlight_cases(window_days=window_days, limit=10)
        now = datetime.utcnow()
        period_end = now.date()
        period_start = period_end - timedelta(days=window_days - 1)
        return {
            "window_days": window_days,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "period_label": (
                f"{period_start.strftime('%Y年%m月%d日')} – "
                f"{period_end.strftime('%Y年%m月%d日')}"
            ),
            "stats": stats,
            "highlight_cases": cases,
            "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
            "disclaimer": stats.get("disclaimer")
            or "历史验证统计仅供参考，不构成投资建议，也不代表未来表现。",
        }

    def get_user_weekly_recap_payload(
        self,
        user_id: str,
        window_days: int = 7,
    ) -> Dict[str, Any]:
        """Aggregate weekly recap for a single user (private, identity-bound)."""
        window_days = min(max(int(window_days or 7), 7), 30)
        stats = self._aggregate_user_stats(user_id, window_days=window_days)
        cases = self._fetch_highlight_cases(
            window_days=window_days,
            limit=10,
            user_id=user_id,
        )
        now = datetime.utcnow()
        period_end = now.date()
        period_start = period_end - timedelta(days=window_days - 1)
        return {
            "scope": "user",
            "user_id": user_id,
            "window_days": window_days,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "period_label": (
                f"{period_start.strftime('%Y年%m月%d日')} – "
                f"{period_end.strftime('%Y年%m月%d日')}"
            ),
            "stats": stats,
            "highlight_cases": cases,
            "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
            "disclaimer": (
                "以下为你个人判断日记在近一周内的复盘统计，仅供参考，"
                "不构成投资建议，也不代表未来表现。"
            ),
        }

    def _aggregate_user_stats(self, user_id: str, *, window_days: int) -> Dict[str, Any]:
        from services.journal.condition_quality import build_condition_quality_leaderboard
        from services.journal.failure_reasons import failure_reason_label, normalize_failure_reason

        outcome_counts = {"supported": 0, "falsified": 0, "uncertain": 0}
        reviewed_condition_items: List[Dict[str, Any]] = []
        failure_reason_counts: Dict[str, int] = {}
        reviewed_count = 0
        pending_count = 0

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT candidate, status, review, constraints, created_at
                FROM judgments
                WHERE user_id = ?
                  AND datetime(created_at) >= datetime('now', ?)
                ORDER BY created_at DESC
                LIMIT 500
                """,
                (user_id, f"-{window_days} day"),
            )
            rows = [dict(row) for row in cursor.fetchall()]

        for row in rows:
            if row.get("status") != "reviewed":
                pending_count += 1
                continue

            review = self._parse_json(row.get("review")) or {}
            outcome = review.get("outcome")
            if outcome not in outcome_counts:
                outcome = "uncertain"
            outcome_counts[outcome] += 1
            reviewed_count += 1

            constraints = self._parse_json(row.get("constraints")) or {}
            candidate = str(row.get("candidate") or "").upper()
            reviewed_condition_items.append(
                {
                    "outcome": outcome,
                    "condition_description": extract_selected_condition_description(
                        constraints,
                        candidate,
                    ),
                }
            )

            failure_reason = normalize_failure_reason(review.get("failure_reason"))
            if failure_reason:
                failure_reason_counts[failure_reason] = failure_reason_counts.get(failure_reason, 0) + 1

        support_rate = None
        falsified_rate = None
        if reviewed_count > 0:
            support_rate = round(outcome_counts["supported"] / reviewed_count * 100, 2)
            falsified_rate = round(outcome_counts["falsified"] / reviewed_count * 100, 2)

        most_common_failure = None
        if failure_reason_counts:
            most_common_failure = max(failure_reason_counts, key=failure_reason_counts.get)

        return {
            "window_days": window_days,
            "reviewed_count": reviewed_count,
            "pending_count": pending_count,
            "outcome_counts": outcome_counts,
            "support_rate": support_rate,
            "falsified_rate": falsified_rate,
            "failure_reason_counts": failure_reason_counts,
            "most_common_failure_reason_label": failure_reason_label(most_common_failure),
            "condition_quality_leaderboard": build_condition_quality_leaderboard(
                reviewed_condition_items
            ),
            "disclaimer": (
                "个人复盘统计仅供参考，不构成投资建议，也不代表未来表现。"
            ),
        }

    def _fetch_highlight_cases(
        self,
        *,
        window_days: int,
        limit: int,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    """
                    SELECT stock_code, candidate, review, constraints, created_at, updated_at
                    FROM judgments
                    WHERE user_id = ?
                      AND status = 'reviewed'
                      AND review IS NOT NULL
                      AND datetime(created_at) >= datetime('now', ?)
                    ORDER BY updated_at DESC
                    LIMIT 120
                    """,
                    (user_id, f"-{window_days} day"),
                )
            else:
                cursor.execute(
                    """
                    SELECT stock_code, candidate, review, constraints, created_at, updated_at
                    FROM judgments
                    WHERE status = 'reviewed'
                      AND review IS NOT NULL
                      AND datetime(created_at) >= datetime('now', ?)
                    ORDER BY updated_at DESC
                    LIMIT 120
                    """,
                    (f"-{window_days} day",),
                )
            rows = [dict(row) for row in cursor.fetchall()]

        cases: List[Dict[str, Any]] = []
        seen_outcomes: Dict[str, int] = {"supported": 0, "falsified": 0, "uncertain": 0}
        max_per_outcome = max(2, limit // 3)

        for row in rows:
            review = self._parse_json(row.get("review")) or {}
            outcome = review.get("outcome") or "uncertain"
            if outcome not in seen_outcomes:
                outcome = "uncertain"
            if seen_outcomes[outcome] >= max_per_outcome and len(cases) >= limit:
                continue

            stock_code = str(row.get("stock_code") or "").strip()
            candidate = str(row.get("candidate") or "").upper()
            constraints = self._parse_json(row.get("constraints")) or {}
            condition = extract_selected_condition_description(constraints, candidate)
            cases.append(
                {
                    "stock_code": stock_code,
                    "candidate": candidate,
                    "outcome": outcome,
                    "outcome_label": self._outcome_label(outcome),
                    "condition": condition or "结构前提判断",
                    "reviewed_at": str(row.get("updated_at") or row.get("created_at") or "")[:10],
                }
            )
            seen_outcomes[outcome] += 1
            if len(cases) >= limit:
                break
        return cases

    def get_latest_weekly_recap_article(self) -> Optional[Dict[str, Any]]:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                row = cursor.execute(
                    """
                    SELECT id, title, publish_date, stock_code, stock_name
                    FROM articles
                    WHERE stock_code = 'WEEKLY_RECAP'
                    ORDER BY publish_date DESC, id DESC
                    LIMIT 1
                    """
                ).fetchone()
            return dict(row) if row else None
        except Exception as exc:
            logger.warning(f"[JudgmentRecap] latest article lookup failed: {exc}")
            return None

    def render_weekly_recap_page(self, window_days: int = 7) -> str:
        payload = self.get_weekly_recap_payload(window_days=window_days)
        stats = payload["stats"]
        reviewed_count = int(stats.get("reviewed_count") or 0)
        support_rate = stats.get("support_rate")
        outcome_counts = stats.get("outcome_counts") or {}
        leaderboard = stats.get("condition_quality_leaderboard") or []
        cases_html = self._render_cases(payload["highlight_cases"])
        leaderboard_html = self._render_leaderboard(leaderboard)
        stats_summary = (
            f"近 {payload['window_days']} 天共复盘 {reviewed_count} 条判断，"
            f"系统支持率 {support_rate}%（仅供参考）"
            if reviewed_count > 0 and support_rate is not None
            else "近一周复盘样本仍在积累中，请以实时诊断与判断日记为准。"
        )
        json_ld = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": "Agu AI 判断验证周报",
                "description": stats_summary,
                "dateModified": payload["generated_at"],
                "publisher": {"@type": "Organization", "name": "Agu AI"},
            },
            ensure_ascii=False,
        )

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI 判断验证周报 - Agu AI</title>
  <meta name="description" content="{self._escape(stats_summary)}">
  <link rel="canonical" href="{self.base_url}/review/weekly">
  <script type="application/ld+json">{json_ld}</script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; color: #101828; background: #f5f7fb; }}
    .nav-shell {{ background: rgba(255,255,255,0.92); border-bottom: 1px solid rgba(61,91,204,0.08); }}
    .nav-inner {{ max-width: 960px; margin: 0 auto; padding: 14px 20px; display: flex; gap: 16px; align-items: center; }}
    .brand {{ font-weight: 700; color: #3d5bcc; text-decoration: none; }}
    .nav-links a {{ margin-right: 14px; color: #475467; text-decoration: none; }}
    .page {{ max-width: 960px; margin: 0 auto; padding: 28px 20px 48px; }}
    .hero {{ background: #fff; border-radius: 20px; padding: 28px; border: 1px solid rgba(61,91,204,0.10); }}
    h1 {{ margin: 0 0 12px; font-size: 30px; }}
    h2 {{ margin: 0 0 12px; font-size: 22px; }}
    section {{ margin-top: 20px; background: #fff; border-radius: 20px; padding: 24px; border: 1px solid rgba(61,91,204,0.10); }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 16px; }}
    .metric {{ background: #f8faff; border-radius: 14px; padding: 14px; }}
    .metric strong {{ display: block; font-size: 24px; color: #3d5bcc; }}
    .case-list, .leaderboard {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }}
    .case-item, .leaderboard-item {{ padding: 14px 16px; border-radius: 14px; background: #f8faff; border: 1px solid rgba(61,91,204,0.10); }}
    .tag {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; margin-right: 8px; }}
    .tag-supported {{ background: #ecfdf3; color: #027a48; }}
    .tag-falsified {{ background: #fef3f2; color: #b42318; }}
    .tag-uncertain {{ background: #f2f4f7; color: #475467; }}
    .disclaimer {{ color: #667085; font-size: 14px; line-height: 1.7; }}
    .cta {{ display: inline-block; margin-top: 12px; padding: 10px 16px; background: #3d5bcc; color: #fff; text-decoration: none; border-radius: 10px; }}
    .cta-secondary {{ background: #eef2ff; color: #3d5bcc; margin-left: 10px; }}
    .cta-row {{ margin-top: 12px; }}
  </style>
</head>
<body>
  <header class="nav-shell">
    <div class="nav-inner">
      <a class="brand" href="/">Agu AI</a>
      <nav class="nav-links" aria-label="主导航">
        <a href="/analysis">分析专栏</a>
        <a href="/journal">判断日记</a>
        <a href="/help/judgment-verification">验证说明</a>
      </nav>
    </div>
  </header>
  <main class="page">
    <header class="hero">
      <p class="disclaimer">统计周期：{self._escape(payload['period_label'])}</p>
      <h1>AI 判断验证周报</h1>
      <p>{self._escape(stats_summary)}</p>
      <p class="disclaimer">{self._escape(payload['disclaimer'])}</p>
      <div class="cta-row">
        <a class="cta" href="/journal">打开判断日记</a>
        <a class="cta cta-secondary" href="/me">用户中心</a>
      </div>
    </header>
    <section>
      <h2>复盘结果分布</h2>
      <div class="metrics">
        <div class="metric"><strong>{outcome_counts.get('supported', 0)}</strong>系统支持</div>
        <div class="metric"><strong>{outcome_counts.get('falsified', 0)}</strong>前提被否定</div>
        <div class="metric"><strong>{outcome_counts.get('uncertain', 0)}</strong>结果不确定</div>
        <div class="metric"><strong>{reviewed_count}</strong>复盘总数</div>
      </div>
    </section>
    <section>
      <h2>典型复盘案例</h2>
      {cases_html}
    </section>
    <section>
      <h2>条件类型表现（样本来自真实复盘）</h2>
      {leaderboard_html}
    </section>
    <section>
      <h2>数据说明</h2>
      <p class="disclaimer">
        本页数据全部来自 Agu AI 判断验证器对用户已复盘记录的结构化统计，仅反映历史样本，
        不代表未来收益或买卖建议。生成时间：{self._escape(payload['generated_at'])}。
      </p>
    </section>
  </main>
</body>
</html>"""

    def log_weekly_snapshot(self, window_days: int = 7) -> Dict[str, Any]:
        payload = self.get_weekly_recap_payload(window_days=window_days)
        reviewed = int(payload["stats"].get("reviewed_count") or 0)
        logger.info(
            f"[JudgmentRecap] weekly snapshot period={payload['period_label']} "
            f"reviewed={reviewed} cases={len(payload['highlight_cases'])}"
        )
        return {
            "period_label": payload["period_label"],
            "reviewed_count": reviewed,
            "cases": len(payload["highlight_cases"]),
        }

    def build_weekly_recap_article(self, window_days: int = 7) -> Dict[str, Any]:
        payload = self.get_weekly_recap_payload(window_days=window_days)
        stats = payload["stats"]
        reviewed_count = int(stats.get("reviewed_count") or 0)
        support_rate = stats.get("support_rate")
        outcome_counts = stats.get("outcome_counts") or {}
        lines = [
            f"# Agu AI 判断验证周报 · {payload['period_label']}",
            "",
            f"> {payload['disclaimer']}",
            "",
            "## 本周概览",
            "",
        ]
        if reviewed_count > 0 and support_rate is not None:
            lines.append(
                f"近 {payload['window_days']} 天共复盘 **{reviewed_count}** 条判断，"
                f"系统支持率 **{support_rate}%**。"
            )
        else:
            lines.append("本周复盘样本仍在积累中，欢迎先在判断日记完成到期复盘。")
        lines.extend(
            [
                "",
                f"- 前提得到支持：{outcome_counts.get('supported', 0)} 条",
                f"- 前提被否定：{outcome_counts.get('falsified', 0)} 条",
                f"- 结果不确定：{outcome_counts.get('uncertain', 0)} 条",
                "",
                "## 典型复盘案例",
                "",
            ]
        )
        cases = payload.get("highlight_cases") or []
        if cases:
            for case in cases[:6]:
                stock_code = case.get("stock_code") or ""
                lines.append(
                    f"- **{case.get('outcome_label')}** · {stock_code} · "
                    f"{case.get('condition') or '结构前提判断'} "
                    f"（{case.get('reviewed_at') or ''}）"
                )
        else:
            lines.append("- 暂无足够案例，完成更多复盘后将自动纳入周报。")
        lines.extend(
            [
                "",
                "## 延伸阅读",
                "",
                f"- [查看完整周报页面]({self.base_url}/review/weekly)",
                f"- [打开判断日记]({self.base_url}/journal)",
                "",
                f"*生成时间：{payload['generated_at']}*",
            ]
        )
        title = f"Agu AI 判断验证周报 · {payload['period_label']}"
        return {
            "title": title,
            "stock_code": "WEEKLY_RECAP",
            "stock_name": "判断验证周报",
            "market_type": "META",
            "content": "\n".join(lines),
            "publish_date": payload["period_end"],
        }

    def publish_weekly_recap_article(self, window_days: int = 7) -> Dict[str, Any]:
        from services.archive_service import ArchiveService

        article = self.build_weekly_recap_article(window_days=window_days)
        article_id = ArchiveService(db_path=str(self.db_path)).save_article_sync(article)
        logger.info(
            f"[JudgmentRecap] published weekly article id={article_id} title={article['title']}"
        )
        return {
            "article_id": article_id,
            "title": article["title"],
            "publish_date": article["publish_date"],
        }

    def _render_cases(self, cases: List[Dict[str, Any]]) -> str:
        if not cases:
            return '<p class="disclaimer">本周暂无足够复盘案例，欢迎先在判断日记中完成复盘。</p>'
        items = []
        for case in cases:
            outcome = case.get("outcome") or "uncertain"
            tag_class = f"tag-{outcome}"
            stock_code = case.get("stock_code") or ""
            stock_link = (
                f'<a href="{self.base_url}/stock/{self._escape(stock_code)}">{self._escape(stock_code)}</a>'
                if stock_code
                else ""
            )
            items.append(
                f"""<li class="case-item">
                  <span class="tag {tag_class}">{self._escape(case.get('outcome_label') or '')}</span>
                  {stock_link}
                  <div>{self._escape(case.get('condition') or '')}</div>
                  <div class="disclaimer">复盘日期 {self._escape(case.get('reviewed_at') or '')}</div>
                </li>"""
            )
        return f'<ul class="case-list">{"".join(items)}</ul>'

    def _render_leaderboard(self, leaderboard: List[Dict[str, Any]]) -> str:
        rows = [
            item
            for item in leaderboard
            if int(item.get("reviewed_count") or 0) >= 2
        ][:6]
        if not rows:
            return '<p class="disclaimer">条件类型样本不足，待更多复盘后展示。</p>'
        items = []
        for row in rows:
            rate = row.get("support_rate")
            rate_text = f"{rate}%" if rate is not None else "—"
            items.append(
                f"""<li class="leaderboard-item">
                  <strong>{self._escape(str(row.get('label') or '条件类型'))}</strong>
                  <div class="disclaimer">复盘 {int(row.get('reviewed_count') or 0)} 条 · 支持率 {rate_text}</div>
                </li>"""
            )
        return f'<ul class="leaderboard">{"".join(items)}</ul>'

    @staticmethod
    def _outcome_label(outcome: str) -> str:
        return {
            "supported": "系统支持",
            "falsified": "前提被否定",
            "uncertain": "结果不确定",
        }.get(outcome, "结果不确定")

    @staticmethod
    def _parse_json(raw: Any) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                return None
        return None

    @staticmethod
    def _escape(value: Any) -> str:
        return html.escape(str(value or ""), quote=True)
