from fastapi.testclient import TestClient

from services.stock_page_service import StockPageService
from web_server import app


def test_stock_landing_page_returns_server_rendered_html():
    with TestClient(app) as client:
        response = client.get("/stock/600519")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")

    html = response.text
    assert "贵州茅台" in html
    assert "600519" in html
    assert "AI诊股" in html
    assert "结构、趋势、相对强弱和风险线索" in html
    assert "风险提示" in html
    assert "仅供研究参考，不构成投资建议" in html
    assert 'rel="canonical"' in html
    assert 'application/ld+json' in html
    assert '"@type":"FAQPage"' in html.replace(" ", "")
    assert "常见问题" in html
    assert "贵州茅台股票怎么看？" in html
    assert "600519当前 AI 诊断关注什么？" in html
    assert "主要风险是什么？" in html
    assert "数据更新时间是什么？" in html
    assert "faq-section" in html
    assert "faq-question" in html
    assert "/?code=600519&amp;market=A&amp;focus=search" in html
    assert "<style>" in html
    assert "linear-gradient" in html
    assert "最近 AI 诊断沉淀" in html
    assert "nav-shell" in html
    assert "分析专栏" in html
    assert "我的观察" in html
    assert "判断日记" in html
    assert "关于我们" in html
    assert '<div id="app"></div>' not in html


def test_stock_landing_page_supports_more_hot_stocks():
    service = StockPageService()
    stocks = service.list_hot_stocks()
    codes = [stock.code for stock in stocks]

    assert len(stocks) >= 100
    assert len(codes) == len(set(codes))

    cases = {
        "000001": "平安银行",
        "300750": "宁德时代",
        "601318": "中国平安",
        "600036": "招商银行",
        "000858": "五粮液",
        "002594": "比亚迪",
        "601899": "紫金矿业",
        "600900": "长江电力",
        "688981": "中芯国际",
        "601398": "工商银行",
        "603501": "韦尔股份",
    }

    with TestClient(app) as client:
        for code, name in cases.items():
            response = client.get(f"/stock/{code}")
            assert response.status_code == 200
            assert name in response.text
            assert code in response.text


def test_stock_index_page_lists_hot_stock_links():
    with TestClient(app) as client:
        response = client.get("/stocks")

    assert response.status_code == 200
    html = response.text
    assert "热门个股 AI 诊股清单" in html
    assert "/stock/600519" in html
    assert "贵州茅台" in html
    assert "/stock/002594" in html
    assert "比亚迪" in html
    assert "nav-shell" in html
    assert "stock-index-grid" in html
    assert "stock-index-item" in html
    assert "/risk-stocks" in html
    assert "风险股清单" in html
    assert "article-card" not in html[html.index("热门股票列表"):]


def test_sitemap_includes_stock_index_and_hot_stock_pages():
    with TestClient(app) as client:
        response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert "https://aguai.net/stocks" in response.text
    assert "https://aguai.net/risk-stocks" in response.text
    assert "https://aguai.net/stock/600519" in response.text
    assert "https://aguai.net/stock/002594" in response.text
    assert "https://aguai.net/stock/688981" in response.text


def test_stock_landing_page_lists_recent_articles(monkeypatch):
    async def fake_get_articles(self, limit=20, offset=0, keyword=None):
        assert limit == 5
        assert keyword == "600519"
        return [
            {
                "id": 11,
                "title": "贵州茅台结构观察",
                "publish_date": "2026-06-15",
                "score": 78,
            },
            {
                "id": 10,
                "title": "贵州茅台量价复盘",
                "publish_date": "2026-06-14",
                "score": 72,
            },
        ]

    monkeypatch.setattr(
        "services.archive_service.ArchiveService.get_articles",
        fake_get_articles,
    )

    with TestClient(app) as client:
        response = client.get("/stock/600519")

    html = response.text
    assert response.status_code == 200
    assert "贵州茅台结构观察" in html
    assert "贵州茅台量价复盘" in html
    assert "/analysis/11" in html
    assert "评分 78" in html


def test_stock_landing_page_faq_uses_ai_score_insights(monkeypatch):
    ai_score = {
        "version": "1.0.0",
        "overall": {"score": 78, "label": "结构偏强", "confidence": 0.82, "degraded": False},
        "dimensions": [
            {
                "id": "risk",
                "name": "风险",
                "score": 55,
                "weight": 0.2,
                "evidence": ["波动率处于近一年高位", "量价出现背离信号"],
                "available": True,
                "degraded": False,
            }
        ],
        "explain": {
            "one_liner": "结构尚可，但波动与量价需继续观察。",
            "notes": [],
        },
    }

    async def fake_get_articles(self, limit=20, offset=0, keyword=None):
        assert keyword == "600519"
        return [
            {
                "id": 11,
                "title": "贵州茅台结构观察",
                "publish_date": "2026-06-15",
                "score": 78,
                "ai_score_json": __import__("json").dumps(ai_score, ensure_ascii=False),
            }
        ]

    monkeypatch.setattr(
        "services.archive_service.ArchiveService.get_articles",
        fake_get_articles,
    )

    with TestClient(app) as client:
        response = client.get("/stock/600519")

    html = response.text
    assert response.status_code == 200
    assert "结构尚可，但波动与量价需继续观察。" in html
    assert "波动率处于近一年高位" in html
    assert "量价出现背离信号" in html
    assert "综合评级为「结构偏强」" in html
    assert "最近一次 AI 诊断沉淀日期为 2026-06-15" in html


def test_stock_landing_page_supports_stocks_with_archived_articles(monkeypatch):
    async def fake_get_articles(self, limit=20, offset=0, keyword=None):
        assert keyword == "300735"
        return [
            {
                "id": 1586,
                "title": "光弘科技 300735 股票行情走势异动分析",
                "stock_code": "300735",
                "stock_name": "光弘科技",
                "market_type": "A",
                "publish_date": "2026-06-17",
                "score": 64,
            }
        ]

    monkeypatch.setattr(
        "services.archive_service.ArchiveService.get_articles",
        fake_get_articles,
    )

    with TestClient(app) as client:
        response = client.get("/stock/300735")

    assert response.status_code == 200
    assert "光弘科技" in response.text
    assert "300735" in response.text
    assert "/analysis/1586" in response.text


def test_stock_landing_page_returns_404_for_unknown_stock():
    with TestClient(app) as client:
        response = client.get("/stock/not-a-stock")

    assert response.status_code == 404
