from pathlib import Path

from fastapi.testclient import TestClient

from web_server import app


def test_frontend_index_has_modern_seo_defaults():
    repo_root = Path(__file__).resolve().parents[1]
    index_text = (repo_root / "frontend/index.html").read_text(encoding="utf-8")

    assert '<title>免费AI在线股票分析平台系统 - 智能诊股助手_软件</title>' in index_text
    assert '<meta name="description"' in index_text
    assert '<link rel="canonical"' in index_text
    assert 'property="og:title"' in index_text
    assert 'property="og:description"' in index_text
    assert 'property="og:url"' in index_text
    assert 'name="twitter:card"' in index_text
    assert '智能股票分析' in index_text or 'AI分析' in index_text


def test_public_index_does_not_disable_zoom():
    repo_root = Path(__file__).resolve().parents[1]
    public_index_text = (repo_root / "frontend/public/index.html").read_text(encoding="utf-8")

    assert "user-scalable=no" not in public_index_text
    assert "maximum-scale=1.0" not in public_index_text


def test_analysis_list_uses_real_links_and_seo_excerpt_helper():
    repo_root = Path(__file__).resolve().parents[1]
    analysis_list_text = (repo_root / "frontend/src/components/AnalysisList.vue").read_text(encoding="utf-8")

    assert "<router-link" in analysis_list_text
    assert "@/utils/seo" in analysis_list_text
    assert "getArticlePreview(" in analysis_list_text
    assert "article.content.substring(0, 100)" not in analysis_list_text
    assert '@click="$router.push(`/analysis/${article.id}`)"' not in analysis_list_text


def test_home_and_article_pages_apply_page_level_seo():
    repo_root = Path(__file__).resolve().parents[1]
    home_text = (repo_root / "frontend/src/components/StockAnalysisApp.vue").read_text(encoding="utf-8")
    article_text = (repo_root / "frontend/src/components/ArticleDetail.vue").read_text(encoding="utf-8")

    assert "@/utils/seo" in home_text
    assert "applyPageSeo({" in home_text
    assert "<h1" in home_text
    assert "免费AI在线股票分析平台系统 - 智能诊股助手_软件" in home_text
    assert home_text.index("analysis-container") < home_text.index("MarketTimeDisplay")
    assert home_text.index("analysis-container") < home_text.index("ValueLoop")

    assert "setCanonicalUrl(" in article_text
    assert "twitter:card" in article_text
    assert "og:url" in article_text
    assert '"@type": "BreadcrumbList"' in article_text


def test_private_pages_expose_error_states_and_noindex_directives():
    repo_root = Path(__file__).resolve().parents[1]
    user_center_text = (repo_root / "frontend/src/components/UserCenter/UserCenterPage.vue").read_text(encoding="utf-8")
    journal_text = (repo_root / "frontend/src/components/Journal/JournalList.vue").read_text(encoding="utf-8")
    watchlist_text = (repo_root / "frontend/src/components/Watchlist/WatchlistList.vue").read_text(encoding="utf-8")

    assert "errorMessage" in user_center_text
    assert "加载用户中心失败" in user_center_text
    assert "applyPageSeo({" in user_center_text
    assert "robots: 'noindex, nofollow'" in user_center_text

    assert "errorMessage" in journal_text
    assert "加载判断日记失败" in journal_text
    assert "applyPageSeo({" in journal_text
    assert "robots: 'noindex, nofollow'" in journal_text

    assert "applyPageSeo({" in watchlist_text
    assert "robots: 'noindex, nofollow'" in watchlist_text


def test_sitemap_and_robots_are_accessible_for_crawlers():
    with TestClient(app) as client:
        sitemap = client.get("/sitemap.xml")
        robots = client.get("/robots.txt")

    assert sitemap.status_code == 200
    assert sitemap.headers["content-type"].startswith("application/xml")
    assert "<urlset" in sitemap.text
    assert "https://aguai.net/analysis" in sitemap.text

    assert robots.status_code == 200
    assert "Sitemap: https://aguai.net/sitemap.xml" in robots.text
