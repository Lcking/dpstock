from pathlib import Path


def test_stock_card_uses_async_chart_module():
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / "frontend/src/components/StockCard.vue").read_text(encoding="utf-8")

    assert "defineAsyncComponent" in text
    assert "StockKlineChartAsync" in text
    assert "@/components/charts/StockKlineChart.vue" in text
    assert "echarts/core" not in text
    assert "initECharts" not in text


def test_chart_modules_use_lazy_echarts_loader():
    repo_root = Path(__file__).resolve().parents[1]
    for rel in (
        "frontend/src/components/charts/StockKlineChart.vue",
        "frontend/src/components/charts/ArticleKlineChart.vue",
    ):
        text = (repo_root / rel).read_text(encoding="utf-8")
        assert "@/utils/echartsLoader" in text
        assert "echarts/charts" not in text


def test_article_detail_uses_async_chart_module():
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / "frontend/src/components/ArticleDetail.vue").read_text(encoding="utf-8")

    assert "defineAsyncComponent" in text
    assert "ArticleKlineChartAsync" in text
    assert "@/components/charts/ArticleKlineChart.vue" in text
    assert "echarts/core" not in text
    assert "initECharts" not in text


def test_vite_manual_chunks_has_ui_and_echarts_split():
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / "frontend/vite.config.ts").read_text(encoding="utf-8")

    assert "vendor-echarts" in text
    assert "vendor-naive-ui" in text
    assert "vendor-icons" in text
    assert "vendor-axios" in text
    assert "vendor-naive-heavy" not in text


def test_frontend_build_metrics_scripts_and_runbook_exist():
    repo_root = Path(__file__).resolve().parents[1]
    pkg_text = (repo_root / "frontend/package.json").read_text(encoding="utf-8")
    runbook_text = (repo_root / "docs/FRONTEND_CHUNK_SAFE_RELEASE.md").read_text(encoding="utf-8")

    assert "build:with-metrics" in pkg_text
    assert "metrics:record" in pkg_text
    assert "record-build-metrics.mjs" in pkg_text
    assert "回滚步骤" in runbook_text
    assert "ChunkLoadError" in runbook_text
