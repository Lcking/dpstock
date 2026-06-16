from fastapi.testclient import TestClient

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
    assert "/?code=600519&amp;market=A&amp;focus=search" in html
    assert "<style>" in html
    assert "linear-gradient" in html
    assert "最近 AI 诊断沉淀" in html
    assert '<div id="app"></div>' not in html


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


def test_stock_landing_page_returns_404_for_unknown_stock():
    with TestClient(app) as client:
        response = client.get("/stock/not-a-stock")

    assert response.status_code == 404
