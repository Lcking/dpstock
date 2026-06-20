"""
Article page SEO + SSR body rendering for /analysis/{id}.
"""
from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, Optional

from services.seo_head_injection import inject_ssr_fields
from services.instrument_name_resolver import enrich_article_record


class ArticleSeoService:
    def __init__(self, base_url: str = "https://aguai.net"):
        self.base_url = base_url.rstrip("/")

    def build_description(self, article: Dict[str, Any]) -> str:
        stock_name = article.get("stock_name") or ""
        stock_code = article.get("stock_code") or ""
        score = article.get("score")
        score_text = f"综合评分 {score}" if score is not None else "综合评分待补充"

        parsed = self._parse_article_content(article.get("content") or "")
        trend_desc = ""
        if parsed:
            structure = parsed.get("structure_snapshot") or {}
            trend_desc = str(structure.get("trend_description") or "").strip()
        if trend_desc:
            return (
                f"{stock_name}({stock_code}) 当日行情深度分析，{score_text}。"
                f"{trend_desc[:150]}..."
            )
        return f"{stock_name}({stock_code}) 当日行情深度分析，{score_text}。"

    def build_json_ld(self, article: Dict[str, Any], description: str) -> Dict[str, Any]:
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": article.get("title") or "",
            "description": description,
            "datePublished": article.get("publish_date") or article.get("created_at") or "",
            "author": {
                "@type": "Organization",
                "name": "Agu AI",
                "url": self.base_url,
            },
            "publisher": {
                "@type": "Organization",
                "name": "Agu AI 股票分析平台",
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{self.base_url}/favicon.ico",
                },
            },
            "about": {
                "@type": "FinancialProduct",
                "name": article.get("stock_name") or "",
                "identifier": article.get("stock_code") or "",
                "category": f"{article.get('market_type') or 'A'}股",
            },
            "keywords": (
                f"{article.get('stock_name')}, {article.get('stock_code')}, "
                f"股票分析, AI分析, {article.get('market_type') or 'A'}股"
            ),
            "articleBody": str(article.get("content") or "")[:500],
        }

    def inject_article_page(self, html_content: str, article: Dict[str, Any]) -> str:
        article = enrich_article_record(article)
        article_id = article.get("id")
        title = f"{article.get('title') or '分析文章'} - Agu AI"
        description = self.build_description(article)
        canonical_url = f"{self.base_url}/analysis/{article_id}"
        keywords = (
            f"{article.get('stock_name')}, {article.get('stock_code')}, "
            "股票分析, AI分析, Agu AI"
        )
        body_html = self.render_article_body(article, description)
        json_ld = self.build_json_ld(article, description)
        json_ld_script = (
            f'\n<script type="application/ld+json">\n'
            f"{json.dumps(json_ld, ensure_ascii=False, indent=2)}\n"
            f"</script>\n"
        )

        return inject_ssr_fields(
            html_content,
            {
                "TITLE": title,
                "DESCRIPTION": description,
                "KEYWORDS": keywords,
                "OG_TITLE": title,
                "OG_DESCRIPTION": description,
                "OG_URL": canonical_url,
                "TWITTER_TITLE": title,
                "TWITTER_DESCRIPTION": description,
                "CANONICAL": canonical_url,
                "ARTICLE_BODY": body_html,
                "JSON_LD": json_ld_script,
            },
            raw_keys={"ARTICLE_BODY", "JSON_LD"},
        )

    def render_article_body(self, article: Dict[str, Any], description: str) -> str:
        article = enrich_article_record(article)
        parsed = self._parse_article_content(article.get("content") or "")
        stock_name = html.escape(str(article.get("stock_name") or ""))
        stock_code = html.escape(str(article.get("stock_code") or ""))
        title = html.escape(str(article.get("title") or "分析文章"))
        publish_date = html.escape(
            str(article.get("publish_date") or article.get("created_at") or "")
        )
        score = article.get("score")
        score_line = (
            f"<p><strong>综合评分：</strong>{html.escape(str(score))}</p>"
            if score is not None
            else ""
        )

        sections = [f"<p>{html.escape(description)}</p>"]
        if parsed:
            structure = parsed.get("structure_snapshot") or {}
            trend_desc = str(structure.get("trend_description") or "").strip()
            if trend_desc:
                sections.append(
                    f"<p><strong>结构趋势：</strong>{html.escape(trend_desc)}</p>"
                )

            judgment = parsed.get("judgment_zone") or {}
            candidates = judgment.get("candidates") or []
            if isinstance(candidates, list) and candidates:
                first = candidates[0]
                if isinstance(first, dict):
                    candidate_desc = str(first.get("description") or "").strip()
                    if candidate_desc:
                        sections.append(
                            "<p><strong>判断关注：</strong>"
                            f"{html.escape(candidate_desc[:240])}</p>"
                        )

            risk_section = parsed.get("risk_section") or {}
            risk_items = risk_section.get("risk_items") or risk_section.get("items") or []
            if isinstance(risk_items, list) and risk_items:
                first_risk = risk_items[0]
                if isinstance(first_risk, dict):
                    risk_text = str(first_risk.get("description") or first_risk.get("title") or "").strip()
                    if risk_text:
                        sections.append(
                            f"<p><strong>主要风险：</strong>{html.escape(risk_text[:240])}</p>"
                        )

        sections.append(
            '<p class="disclaimer">本内容仅供研究参考，不构成投资建议。市场有风险，投资需谨慎。</p>'
        )

        return (
            '<article id="ssr-article" class="ssr-article">'
            f"<h1>{title}</h1>"
            f'<p class="ssr-meta">{stock_name} ({stock_code}) · {publish_date}</p>'
            f"{score_line}"
            f"{''.join(sections)}"
            "</article>"
        )

    def _parse_article_content(self, content: str) -> Optional[Dict[str, Any]]:
        text = str(content or "").strip()
        if not text:
            return None
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
