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
    assert "/?code=600519&amp;market=A" in html
    assert "智能搜索与选择" not in html


def test_stock_landing_page_returns_404_for_unknown_stock():
    with TestClient(app) as client:
        response = client.get("/stock/not-a-stock")

    assert response.status_code == 404
