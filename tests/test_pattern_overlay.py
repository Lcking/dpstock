"""Pattern overlay: kline API 下发形态标注数据 + 前端渲染契约。"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from services.stock_analyzer_service import StockAnalyzerService

REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_double_bottom_df(rows: int = 80) -> pd.DataFrame:
    """构造一个带双底结构的 OHLCV + MA DataFrame。"""
    rng = np.random.default_rng(7)
    base = np.concatenate([
        np.linspace(110, 100, 20),   # 下跌到低点1
        np.linspace(100, 106, 12),   # 反弹（颈线）
        np.linspace(106, 100.5, 12), # 回落到低点2
        np.linspace(100.5, 108, rows - 44),  # 突破
    ])
    noise = rng.normal(0, 0.15, rows)
    close = base + noise
    dates = pd.date_range('2026-01-01', periods=rows, freq='B')
    df = pd.DataFrame({
        'Open': close - 0.2,
        'Close': close,
        'High': close + 0.5,
        'Low': close - 0.5,
        'Volume': rng.integers(1_000_000, 5_000_000, rows).astype(float),
    }, index=dates)
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    return df


def test_build_pattern_overlay_returns_renderable_structure():
    service = StockAnalyzerService()
    df = _make_double_bottom_df()

    overlay = service._build_pattern_overlay(df)

    assert set(overlay.keys()) == {"patterns", "crossovers", "swing_points"}
    assert isinstance(overlay["patterns"], list)
    assert len(overlay["patterns"]) <= 2

    for pattern in overlay["patterns"]:
        assert pattern["confidence"] >= 50
        assert pattern["label"]
        for point in pattern["points"]:
            assert point["date"]  # 有日期的点必须能定位到 x 轴
            assert isinstance(point["price"], float)
        for line in pattern["lines"]:
            assert isinstance(line["price"], float)

    for cross in overlay["crossovers"]:
        assert cross["cross_type"] in ("golden_cross", "death_cross")
        assert cross["date"]


def test_build_pattern_overlay_handles_tiny_dataframe():
    service = StockAnalyzerService()
    rows = 10
    dates = pd.date_range('2026-01-01', periods=rows, freq='B')
    close = np.linspace(100, 105, rows)
    df = pd.DataFrame({
        'Open': close - 0.2,
        'Close': close,
        'High': close + 0.5,
        'Low': close - 0.5,
        'Volume': np.full(rows, 1_000_000.0),
    }, index=dates)
    overlay = service._build_pattern_overlay(df)
    assert overlay == {"patterns": [], "crossovers": [], "swing_points": []}


def test_extract_pattern_label():
    assert StockAnalyzerService._extract_pattern_label("**双顶形态**：xxx") == "双顶形态"
    assert StockAnalyzerService._extract_pattern_label("没有粗体") == ""
    assert StockAnalyzerService._extract_pattern_label(None) == ""


@pytest.mark.asyncio
async def test_kline_data_includes_pattern_overlay(monkeypatch):
    service = StockAnalyzerService()
    df = _make_double_bottom_df()

    async def fake_get_stock_data(*args, **kwargs):
        return df

    monkeypatch.setattr(service.data_provider, "get_stock_data", fake_get_stock_data)

    data = await service.get_kline_data("600519", "A", days=80)
    assert "pattern_overlay" in data
    assert set(data["pattern_overlay"].keys()) == {"patterns", "crossovers", "swing_points"}


def test_frontend_charts_render_pattern_overlay():
    overlay_util = (REPO_ROOT / "frontend/src/utils/patternOverlay.ts").read_text(encoding="utf-8")
    assert "buildOverlayMarks" in overlay_util
    assert "markLine" in overlay_util
    assert "markPoint" in overlay_util

    for rel in (
        "frontend/src/components/charts/ArticleKlineChart.vue",
        "frontend/src/components/charts/StockKlineChart.vue",
    ):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "buildOverlayMarks" in text, rel
        assert "pattern_overlay" in text, rel
        assert "markLine" in text, rel
        assert "pattern-legend" in text, rel

    loader = (REPO_ROOT / "frontend/src/utils/echartsLoader.ts").read_text(encoding="utf-8")
    assert "MarkLineComponent" in loader
    assert "MarkPointComponent" in loader
    assert "DataZoomInsideComponent" in loader
    assert "DataZoomSliderComponent" in loader


def test_frontend_charts_support_zooming_for_crowded_marks():
    for rel in (
        "frontend/src/components/charts/ArticleKlineChart.vue",
        "frontend/src/components/charts/StockKlineChart.vue",
    ):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "dataZoom" in text, rel
        assert "'inside'" in text, rel
        assert "'slider'" in text, rel
        assert "silent: true" not in text, rel
