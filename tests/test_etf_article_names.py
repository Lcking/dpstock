from services.article_seo_service import ArticleSeoService
from services.instrument_name_resolver import enrich_article_record, resolve_stock_page_info


def test_enrich_article_record_resolves_etf_name(monkeypatch):
    monkeypatch.setattr(
        "services.instrument_name_resolver.lookup_fund_name",
        lambda code, market_type="ETF": "创业板ETF" if code == "159915" else "",
    )

    enriched = enrich_article_record(
        {
            "id": 1607,
            "stock_code": "159915",
            "stock_name": "",
            "market_type": "ETF",
            "title": "2026年06月19日 159915 ETF行情走势异动分析",
        }
    )

    assert enriched["stock_name"] == "创业板ETF"


def test_article_seo_body_shows_resolved_etf_name(monkeypatch):
    monkeypatch.setattr(
        "services.instrument_name_resolver.lookup_fund_name",
        lambda code, market_type="ETF": "纳指ETF" if code == "159941" else "",
    )

    article = {
        "id": 1605,
        "title": "2026年06月19日 159941 ETF行情走势异动分析",
        "stock_code": "159941",
        "stock_name": "",
        "market_type": "ETF",
        "publish_date": "2026-06-19",
        "score": 60,
        "content": "",
    }
    body = ArticleSeoService().render_article_body(article, "测试描述")
    assert "纳指ETF" in body
    assert "159941" in body


def test_resolve_stock_page_info_uses_fallback_when_lookup_missing():
    resolved = resolve_stock_page_info("999999", stock_name="", market_type="ETF")
    assert resolved is not None
    code, name, market = resolved
    assert code == "999999"
    assert name == "ETF 999999"
    assert market == "ETF"


def test_stock_page_from_archived_etf_article(monkeypatch):
    from fastapi.testclient import TestClient
    from web_server import app

    async def fake_get_articles(self, limit=20, offset=0, keyword=None):
        assert keyword == "159915"
        return [
            {
                "id": 1607,
                "title": "2026年06月19日 159915 ETF行情走势异动分析",
                "stock_code": "159915",
                "stock_name": "",
                "market_type": "ETF",
                "publish_date": "2026-06-19",
                "score": 59,
            }
        ]

    monkeypatch.setattr(
        "services.archive_service.ArchiveService.get_articles",
        fake_get_articles,
    )
    monkeypatch.setattr(
        "services.instrument_name_resolver.lookup_fund_name",
        lambda code, market_type="ETF": "创业板ETF" if code == "159915" else "",
    )

    with TestClient(app) as client:
        response = client.get("/stock/159915")

    assert response.status_code == 200
    assert "创业板ETF" in response.text
    assert "159915" in response.text
