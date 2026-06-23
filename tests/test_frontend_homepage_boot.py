from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPO_ROOT / "frontend"
DIST_INDEX = FRONTEND_ROOT / "dist" / "index.html"
ASSETS_DIR = FRONTEND_ROOT / "dist" / "assets"


def test_homepage_boot_assets_do_not_preload_echarts():
    assert DIST_INDEX.exists(), "run `cd frontend && npm run build` before this test"
    html = DIST_INDEX.read_text(encoding="utf-8")
    assert "vendor-echarts" not in html

    index_chunks = list(ASSETS_DIR.glob("index-*.js"))
    assert index_chunks, "missing index chunk"
    index_source = index_chunks[0].read_text(encoding="utf-8")
    assert "echarts/charts" not in index_source
    assert "vendor-echarts" not in index_source

    home_chunks = list(ASSETS_DIR.glob("StockAnalysisApp-*.js"))
    if home_chunks:
        home_source = home_chunks[0].read_text(encoding="utf-8")
        assert 'from"echarts/' not in home_source
        assert "from 'echarts/" not in home_source
        assert 'import("echarts/' not in home_source


def test_homepage_boot_smoke_script_passes_when_preview_running():
    if not DIST_INDEX.exists():
        return

    script = FRONTEND_ROOT / "scripts" / "smoke-homepage-boot.mjs"
    result = subprocess.run(
        ["node", str(script), "--base-url", "http://127.0.0.1:4173"],
        cwd=FRONTEND_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0 and "ECONNREFUSED" in (result.stderr + result.stdout):
        import pytest

        pytest.skip("preview server not running on :4173; start with `npm run preview`")
    assert result.returncode == 0, result.stdout + result.stderr
