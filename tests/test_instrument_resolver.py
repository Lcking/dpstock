"""
Regression tests for ETF/LOF name resolution and market inference.

Complements tests/test_etf_article_names.py (archive titles, SEO body, stock pages)
by covering market-type matrix, akshare cache loading, and tushare fund_basic fallback.
"""
from __future__ import annotations

import pandas as pd
import pytest

import services.instrument_name_resolver as resolver
from services.article_seo_service import ArticleSeoService
from services.instrument_name_resolver import (
    build_archive_title,
    enrich_article_record,
    infer_market_type,
    lookup_fund_name,
    resolve_display_name,
    resolve_stock_page_info,
)


@pytest.fixture(autouse=True)
def _reset_fund_name_caches():
    resolver._ETF_NAME_CACHE.clear()
    resolver._LOF_NAME_CACHE.clear()
    resolver._CACHE_LOADED_AT.clear()
    resolver._LOAD_FAILURE_UNTIL.clear()
    yield
    resolver._ETF_NAME_CACHE.clear()
    resolver._LOF_NAME_CACHE.clear()
    resolver._CACHE_LOADED_AT.clear()
    resolver._LOAD_FAILURE_UNTIL.clear()


@pytest.mark.parametrize(
    ("code", "declared", "expected"),
    [
        ("510300", "A", "ETF"),
        ("159919", "A", "ETF"),
        ("561500", "A", "ETF"),
        ("588000", "A", "ETF"),
        ("161725", "A", "LOF"),
        ("688001", "A", "A"),
        ("830001", "A", "A"),
        ("00700", "A", "HK"),
        ("AAPL", "A", "US"),
        ("159915", "ETF", "ETF"),
        ("161226", "LOF", "LOF"),
    ],
)
def test_infer_market_type_matrix(code, declared, expected):
    assert infer_market_type(code, declared) == expected


def test_lookup_fund_name_reads_akshare_cache(monkeypatch):
    monkeypatch.setattr(
        resolver,
        "_fetch_fund_mapping",
        lambda market_type: {"510300": "沪深300ETF"} if market_type == "ETF" else {},
    )

    assert lookup_fund_name("510300", "ETF") == "沪深300ETF"


def test_resolve_display_name_falls_back_to_tushare_fund_basic(monkeypatch):
    monkeypatch.setattr(resolver, "lookup_fund_name", lambda code, market_type="ETF": "")

    class _FakeTushareClient:
        def ensure_initialized(self, log_missing_token=False):
            return None

        @property
        def is_available(self):
            return True

        def query(self, api_name, **kwargs):
            assert api_name == "fund_basic"
            assert kwargs["ts_code"] == "510300.SH"
            return pd.DataFrame([{"name": "华泰柏瑞沪深300ETF"}])

    monkeypatch.setattr(
        "services.tushare.client.tushare_client",
        _FakeTushareClient(),
    )

    resolved = resolve_display_name(
        "510300",
        market_type="A",
        stock_name="510300",
        allow_network=True,
    )
    assert resolved == "华泰柏瑞沪深300ETF"


def test_enrich_article_record_uses_tushare_when_cache_miss(monkeypatch):
    monkeypatch.setattr(resolver, "lookup_fund_name", lambda code, market_type="ETF": "")

    class _FakeTushareClient:
        def ensure_initialized(self, log_missing_token=False):
            return None

        @property
        def is_available(self):
            return True

        def query(self, api_name, **kwargs):
            return pd.DataFrame([{"name": "招商中证白酒指数(LOF)A"}])

    monkeypatch.setattr(
        "services.tushare.client.tushare_client",
        _FakeTushareClient(),
    )

    enriched = enrich_article_record(
        {
            "id": 1701,
            "stock_code": "161725",
            "stock_name": "161725",
            "market_type": "A",
            "title": "2026年06月20日 161725 LOF行情走势异动分析",
        }
    )

    assert enriched["market_type"] == "LOF"
    assert enriched["stock_name"] == "招商中证白酒指数(LOF)A"


def test_build_archive_title_infers_etf_suffix_from_code_prefix():
    title = build_archive_title(
        "510300",
        stock_name="510300",
        market_type="A",
        publish_date="2026-06-20",
    )
    assert title == "2026年06月20日 510300 ETF行情走势异动分析"


def test_resolve_stock_page_info_uses_tushare_resolved_name(monkeypatch):
    monkeypatch.setattr(resolver, "lookup_fund_name", lambda code, market_type="ETF": "")

    class _FakeTushareClient:
        def ensure_initialized(self, log_missing_token=False):
            return None

        @property
        def is_available(self):
            return True

        def query(self, api_name, **kwargs):
            return pd.DataFrame([{"name": "华夏上证50ETF"}])

    monkeypatch.setattr(
        "services.tushare.client.tushare_client",
        _FakeTushareClient(),
    )

    resolved = resolve_stock_page_info("510300", stock_name="510300", market_type="A")
    assert resolved == ("510300", "华夏上证50ETF", "ETF")


def test_article_seo_body_shows_tushare_resolved_etf_name(monkeypatch):
    monkeypatch.setattr(resolver, "lookup_fund_name", lambda code, market_type="ETF": "")

    class _FakeTushareClient:
        def ensure_initialized(self, log_missing_token=False):
            return None

        @property
        def is_available(self):
            return True

        def query(self, api_name, **kwargs):
            return pd.DataFrame([{"name": "易方达创业板ETF"}])

    monkeypatch.setattr(
        "services.tushare.client.tushare_client",
        _FakeTushareClient(),
    )

    article = enrich_article_record(
        {
            "id": 1607,
            "title": "2026年06月19日 159915 ETF行情走势异动分析",
            "stock_code": "159915",
            "stock_name": "159915",
            "market_type": "A",
            "publish_date": "2026-06-19",
            "score": 59,
            "content": "",
        }
    )
    body = ArticleSeoService().render_article_body(article, "测试描述")
    assert "易方达创业板ETF" in body
    assert "159915" in body
