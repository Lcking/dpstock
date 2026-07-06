import sqlite3
from pathlib import Path

import pytest

from database.db_factory import DatabaseFactory
from services.archive_service import ArchiveService

REPO_ROOT = Path(__file__).resolve().parents[1]


def _init_articles_table(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                stock_code TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                market_type TEXT NOT NULL,
                content TEXT NOT NULL,
                score INTEGER,
                legacy_score INTEGER,
                score_version TEXT,
                ai_score_json TEXT,
                publish_date TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO articles (
                title, stock_code, stock_name, market_type, content, score, publish_date, created_at
            ) VALUES
            ('公开诊股文章', '159915', '创业板ETF', 'ETF', '{}', 80, '2026-07-01', '2026-07-01'),
            ('判断验证周报', 'WEEKLY_RECAP', '判断验证周报', 'META', '# recap', 0, '2026-07-01', '2026-07-01')
            """
        )
        conn.commit()


@pytest.mark.asyncio
async def test_public_article_list_excludes_weekly_recap(tmp_path):
    db_path = tmp_path / "archive_private.db"
    _init_articles_table(db_path)
    DatabaseFactory.initialize(str(db_path))
    service = ArchiveService(db_path=str(db_path))

    articles = await service.get_articles(limit=20, offset=0)
    assert len(articles) == 1
    assert articles[0]["stock_code"] == "159915"


@pytest.mark.asyncio
async def test_public_article_detail_hides_weekly_recap(tmp_path):
    db_path = tmp_path / "archive_private_detail.db"
    _init_articles_table(db_path)
    DatabaseFactory.initialize(str(db_path))
    service = ArchiveService(db_path=str(db_path))

    hidden = await service.get_article_by_id(2)
    assert hidden is None

    visible = await service.get_article_by_id(1)
    assert visible is not None
    assert visible["stock_code"] == "159915"
