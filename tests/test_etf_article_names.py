from services.article_seo_service import ArticleSeoService
from services.instrument_name_resolver import (
    enrich_article_record,
    infer_market_type,
    is_placeholder_name,
    resolve_display_name,
    resolve_stock_page_info,
)


def test_infer_market_type_detects_etf_from_code_prefix():
    assert infer_market_type("159915", "A") == "ETF"
    assert infer_market_type("513120", "A") == "ETF"
    assert infer_market_type("161226", "A") == "LOF"


def test_is_placeholder_name_treats_code_as_invalid():
    assert is_placeholder_name("159915", "159915") is True
    assert is_placeholder_name("ETF 159915", "159915") is True
    assert is_placeholder_name("易方达创业板ETF", "159915") is False


def test_resolve_display_name_re_resolves_placeholder_name(monkeypatch):
    monkeypatch.setattr(
        "services.instrument_name_resolver.lookup_fund_name",
        lambda code, market_type="ETF": "易方达创业板ETF" if code == "159915" else "",
    )

    resolved = resolve_display_name(
        "159915",
        market_type="A",
        stock_name="159915",
        allow_network=False,
    )
    assert resolved == "易方达创业板ETF"


def test_enrich_article_record_fixes_wrong_market_and_placeholder_name(monkeypatch):
    monkeypatch.setattr(
        "services.instrument_name_resolver.lookup_fund_name",
        lambda code, market_type="ETF": "广发纳斯达克100ETF(QDII)" if code == "159941" else "",
    )

    enriched = enrich_article_record(
        {
            "id": 1605,
            "stock_code": "159941",
            "stock_name": "159941",
            "market_type": "A",
            "title": "2026年06月19日 159941 ETF行情走势异动分析",
        }
    )

    assert enriched["market_type"] == "ETF"
    assert enriched["stock_name"] == "广发纳斯达克100ETF(QDII)"


def test_enrich_article_record_uses_fallback_when_lookup_missing(monkeypatch):
    monkeypatch.setattr(
        "services.instrument_name_resolver.resolve_display_name",
        lambda *args, **kwargs: "",
    )

    enriched = enrich_article_record(
        {
            "id": 1605,
            "stock_code": "159941",
            "stock_name": "",
            "market_type": "ETF",
            "title": "2026年06月19日 159941 ETF行情走势异动分析",
        }
    )

    assert enriched["stock_name"] == "ETF 159941"


def test_resolve_display_name_supports_us_popular_list():
    assert resolve_display_name("AAPL", market_type="US", allow_network=False) == "Apple"


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
