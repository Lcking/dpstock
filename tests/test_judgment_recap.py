import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from database.db_factory import DatabaseFactory
from services.judgment_recap_service import JudgmentRecapService
from services.sitemap_generator import SitemapGenerator


def _create_judgments_table(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE judgments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                stock_code TEXT NOT NULL,
                candidate TEXT,
                selected_premises TEXT,
                selected_risk_checks TEXT,
                constraints TEXT,
                snapshot TEXT,
                validation_date TEXT,
                status TEXT DEFAULT 'active',
                review TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def test_weekly_recap_payload_aggregates_reviewed_cases(tmp_path):
    db_path = tmp_path / "judgment_recap.db"
    DatabaseFactory.initialize(str(db_path))
    _create_judgments_table(db_path)

    created_at = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO judgments (
                id, user_id, stock_code, candidate, selected_premises,
                selected_risk_checks, constraints, snapshot, validation_date,
                status, review, created_at, updated_at
            ) VALUES (?, 'u1', '600519', 'A', '[]', '[]', '{}', '{}', ?, 'reviewed', ?, ?, ?)
            """,
            (
                "jr1",
                created_at,
                json.dumps({"outcome": "supported"}, ensure_ascii=False),
                created_at,
                created_at,
            ),
        )
        conn.commit()

    payload = JudgmentRecapService(base_url="https://aguai.net", db_path=str(db_path)).get_weekly_recap_payload(
        window_days=7
    )

    assert payload["stats"]["reviewed_count"] == 1
    assert len(payload["highlight_cases"]) == 1
    assert payload["highlight_cases"][0]["stock_code"] == "600519"
    assert "仅供参考" in payload["disclaimer"]


def test_weekly_recap_page_is_ssr_html_with_compliance_copy(tmp_path):
    db_path = tmp_path / "judgment_recap_html.db"
    DatabaseFactory.initialize(str(db_path))
    _create_judgments_table(db_path)

    html = JudgmentRecapService(base_url="https://aguai.net", db_path=str(db_path)).render_weekly_recap_page(
        window_days=7
    )

    assert "<title>AI 判断验证周报 - Agu AI</title>" in html
    assert "不构成投资建议" in html
    assert "判断验证周报" in html
    assert 'href="https://aguai.net/stock/' not in html or "复盘样本仍在积累" in html
    assert '"@type": "Article"' in html
    assert 'href="/me"' in html
    assert "阅读归档文章" not in html


def test_core_sitemap_excludes_weekly_recap_page(tmp_path, monkeypatch):
    async def fake_get_articles(self, limit=1000, offset=0):
        return []

    monkeypatch.setattr(
        "services.archive_service.ArchiveService.get_articles",
        fake_get_articles,
    )
    import asyncio

    xml = asyncio.run(SitemapGenerator(base_url="https://aguai.net").generate_core_sitemap())
    assert "https://aguai.net/review/weekly" not in xml


def test_publish_weekly_recap_article_writes_to_archive(tmp_path):
    db_path = tmp_path / "judgment_recap_publish.db"
    DatabaseFactory.initialize(str(db_path))
    _create_judgments_table(db_path)

    from services.archive_service import ArchiveService

    ArchiveService(db_path=str(db_path))

    created_at = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO judgments (
                id, user_id, stock_code, candidate, selected_premises,
                selected_risk_checks, constraints, snapshot, validation_date,
                status, review, created_at, updated_at
            ) VALUES (?, 'u1', '600519', 'A', '[]', '[]', '{}', '{}', ?, 'reviewed', ?, ?, ?)
            """,
            (
                "jr1",
                created_at,
                json.dumps({"outcome": "supported"}, ensure_ascii=False),
                created_at,
                created_at,
            ),
        )
        conn.commit()

    service = JudgmentRecapService(base_url="https://aguai.net", db_path=str(db_path))
    published = service.publish_weekly_recap_article(window_days=7)

    assert published["article_id"] > 0
    assert "判断验证周报" in published["title"]

    public_articles = asyncio.run(ArchiveService(db_path=str(db_path)).get_articles(limit=10))
    assert public_articles == []

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT title, stock_code, market_type FROM articles WHERE title = ?",
            (published["title"],),
        ).fetchone()
    assert row is not None
    assert row[1] == "WEEKLY_RECAP"
    assert row[2] == "META"

