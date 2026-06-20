from pathlib import Path

from services.article_seo_service import ArticleSeoService
from services.seo_head_injection import assert_no_ssr_placeholders_remain


def _sample_index_html() -> str:
    return (Path(__file__).resolve().parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")


def test_article_seo_injection_replaces_all_placeholders():
    article = {
        "id": 42,
        "title": "贵州茅台结构观察",
        "stock_name": "贵州茅台",
        "stock_code": "600519",
        "market_type": "A",
        "score": 78,
        "publish_date": "2026-06-18",
        "content": """```json
{
  "structure_snapshot": {
    "trend_description": "价格维持在关键支撑上方，中期结构仍偏强。"
  }
}
```""",
    }

    service = ArticleSeoService(base_url="https://aguai.net")
    html = service.inject_article_page(_sample_index_html(), article)

    assert "贵州茅台结构观察 - Agu AI" in html
    assert "600519" in html
    assert 'href="https://aguai.net/analysis/42"' in html
    assert 'content="https://aguai.net/analysis/42"' in html
    assert "Agu AI 提供 A 股、港股、美股与 ETF 的智能股票分析" not in html
    assert '<article id="ssr-article"' in html
    assert "不构成投资建议" in html
    assert '"@type": "Article"' in html
    assert '"@type": "FAQPage"' in html
    assert "ssr-faq-section" in html
    assert "常见问题" in html
    assert "主要风险是什么？" in html
    assert "<!--SSR:" not in html
    assert_no_ssr_placeholders_remain(html)


def test_index_html_hides_ssr_article_for_js_users():
    html = _sample_index_html()
    assert "js-enabled" in html
    assert "#ssr-article" in html
    assert "display: none" in html


def test_article_description_uses_trend_text_not_generic_site_copy():
    article = {
        "id": 7,
        "title": "测试文章",
        "stock_name": "测试股份",
        "stock_code": "000001",
        "market_type": "A",
        "score": 66,
        "publish_date": "2026-06-18",
        "content": """```json
{"structure_snapshot": {"trend_description": "短线震荡，量能尚未确认。"}}
```""",
    }

    description = ArticleSeoService().build_description(article)

    assert "测试股份(000001)" in description
    assert "短线震荡" in description
    assert "Agu AI 提供 A 股" not in description
