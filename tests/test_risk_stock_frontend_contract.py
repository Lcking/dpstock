from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_risk_stock_page_has_route_api_and_footer_entry():
    router_text = (REPO_ROOT / "frontend/src/router/index.ts").read_text(encoding="utf-8")
    api_text = (REPO_ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
    footer_text = (REPO_ROOT / "frontend/src/components/Footer.vue").read_text(encoding="utf-8")
    page_text = (REPO_ROOT / "frontend/src/components/RiskStockList.vue").read_text(encoding="utf-8")

    assert "RiskStockList" in router_text
    assert "/risk-stocks" in router_text
    assert "getRiskStocks" in api_text
    assert 'href="/risk-stocks"' in footer_text
    assert "风险股清单" in footer_text
    assert "风险股清单" in page_text
    assert "ST股" in page_text
    assert "三连板" in page_text
    assert "高风险" in page_text
    assert "重新加载" in page_text
