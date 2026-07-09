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

    overlay = service._build_pattern_overlay(df, scope='recent')

    assert set(overlay.keys()) == {"patterns", "crossovers", "swing_points"}
    assert isinstance(overlay["patterns"], list)
    assert len(overlay["patterns"]) <= 2

    for pattern in overlay["patterns"]:
        assert pattern["confidence"] >= 50
        assert pattern["label"]
        assert pattern["scope"] == "recent"
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
    assert set(data["pattern_overlay"].keys()) >= {"patterns", "crossovers", "swing_points", "note"}


def _make_long_history_with_early_hs_top(rows: int = 260) -> pd.DataFrame:
    """前段构造头肩顶（约第 40-80 根），后段再走出另一套低位结构。"""
    rng = np.random.default_rng(11)
    # 头肩顶：左肩20.8 / 头21.58 / 右肩21.1，颈线约19.6
    early = np.concatenate([
        np.linspace(18.0, 20.8, 25),
        np.linspace(20.8, 19.5, 10),
        np.linspace(19.5, 21.58, 12),
        np.linspace(21.58, 19.6, 10),
        np.linspace(19.6, 21.1, 10),
        np.linspace(21.1, 18.5, 15),
    ])
    late = np.concatenate([
        np.linspace(18.5, 15.0, 40),
        np.linspace(15.0, 16.5, 20),
        np.linspace(16.5, 15.1, 20),
        np.linspace(15.1, 21.4, rows - len(early) - 80),
    ])
    close = np.concatenate([early, late]) + rng.normal(0, 0.05, rows)
    dates = pd.date_range('2025-06-01', periods=rows, freq='B')
    df = pd.DataFrame({
        'Open': close - 0.1,
        'Close': close,
        'High': close + 0.35,
        'Low': close - 0.35,
        'Volume': rng.integers(1_000_000, 5_000_000, rows).astype(float),
    }, index=dates)
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    return df


def test_resolve_display_days_extends_for_early_pattern_points():
    service = StockAnalyzerService()
    df = _make_long_history_with_early_hs_top()
    overlay = {
        "patterns": [{
            "points": [
                {"label": "左肩", "price": 20.8, "date": df.index[30].strftime('%Y-%m-%d')},
                {"label": "头部", "price": 21.58, "date": df.index[50].strftime('%Y-%m-%d')},
            ],
            "lines": [{"label": "颈线", "price": 19.6}],
        }],
        "crossovers": [],
        "swing_points": [],
    }
    days = service._resolve_kline_display_days(df, overlay, min_days=100, max_days=300)
    assert days > 100
    assert days <= 300
    # 最早关键点应落在展示窗口内
    display = df.tail(days)
    assert df.index[30].strftime('%Y-%m-%d') in display.index.strftime('%Y-%m-%d').tolist()


def test_clip_overlay_drops_out_of_window_dated_points():
    service = StockAnalyzerService()
    df = _make_double_bottom_df(rows=80)
    overlay = {
        "patterns": [{
            "pattern_type": "head_shoulders",
            "label": "头肩顶形态",
            "confidence": 80,
            "completion_rate": 90,
            "points": [
                {"label": "头部", "price": 21.58, "date": "2024-01-01"},  # 窗外
                {"label": "右肩", "price": 21.1, "date": df.index[10].strftime('%Y-%m-%d')},
            ],
            "lines": [{"label": "颈线", "price": 19.6}],
        }],
        "crossovers": [{"date": "2024-01-01", "cross_type": "golden_cross"}],
        "swing_points": [{"date": df.index[5].strftime('%Y-%m-%d'), "price": 100.0, "type": "high"}],
        "note": "默认展示近期形态；另有全历史形态，可用滚轮/滑条缩小查看",
    }
    clipped = service._clip_pattern_overlay(overlay, df)
    assert len(clipped["patterns"]) == 1
    assert all(p["date"] != "2024-01-01" for p in clipped["patterns"][0]["points"])
    assert clipped["crossovers"] == []
    assert len(clipped["swing_points"]) == 1
    assert "全历史" in clipped["note"]


def test_merge_keeps_both_recent_and_history_when_different():
    service = StockAnalyzerService()
    recent = {
        "patterns": [{
            "scope": "recent",
            "pattern_type": "head_shoulders_bottom",
            "label": "头肩底形态",
            "confidence": 90,
            "completion_rate": 80,
            "points": [
                {"label": "左肩", "price": 16.35, "date": "2026-04-27"},
                {"label": "头部", "price": 15.08, "date": "2026-06-04"},
                {"label": "右肩", "price": 16.32, "date": "2026-06-30"},
            ],
            "lines": [{"label": "颈线", "price": 17.5}],
        }],
        "crossovers": [],
        "swing_points": [],
    }
    history = {
        "patterns": [{
            "scope": "history",
            "pattern_type": "head_shoulders",
            "label": "头肩顶形态",
            "confidence": 90,
            "completion_rate": 90,
            "points": [
                {"label": "左肩", "price": 20.8, "date": "2025-10-09"},
                {"label": "头部", "price": 21.58, "date": "2025-10-28"},
                {"label": "右肩", "price": 21.1, "date": "2025-11-06"},
            ],
            "lines": [{"label": "颈线", "price": 19.6}],
        }],
        "crossovers": [],
        "swing_points": [],
    }
    merged = service._merge_pattern_overlays(recent, history)
    scopes = {p["scope"] for p in merged["patterns"]}
    assert scopes == {"recent", "history"}
    assert "全历史" in merged["note"]
    assert "缩放" in merged["note"] or "滑条" in merged["note"]


@pytest.mark.asyncio
async def test_kline_overlay_includes_both_scopes_when_divergent(monkeypatch):
    """短窗与全历史形态不同时，API 应同时下发两套，并提示可用缩放查看。"""
    service = StockAnalyzerService()
    df = _make_long_history_with_early_hs_top()

    async def fake_get_stock_data(*args, **kwargs):
        return df

    monkeypatch.setattr(service.data_provider, "get_stock_data", fake_get_stock_data)

    full_overlay = service._build_pattern_overlay(df, scope='history')
    window_overlay = service._build_pattern_overlay(df.tail(100), scope='recent')
    data = await service.get_kline_data("301151", "A", days=100)
    overlay = data["pattern_overlay"]

    if full_overlay["patterns"] and window_overlay["patterns"]:
        full_prices = {p["label"]: p["price"] for p in full_overlay["patterns"][0]["points"]}
        win_prices = {p["label"]: p["price"] for p in window_overlay["patterns"][0]["points"]}
        if full_prices != win_prices:
            scopes = {p.get("scope") for p in overlay["patterns"]}
            assert "recent" in scopes
            assert "history" in scopes
            assert overlay.get("note")
            assert "全历史" in overlay["note"]

    for pat in overlay["patterns"]:
        for point in pat["points"]:
            assert point["date"] in data["dates"]


def test_frontend_charts_render_pattern_overlay():
    overlay_util = (REPO_ROOT / "frontend/src/utils/patternOverlay.ts").read_text(encoding="utf-8")
    assert "buildOverlayMarks" in overlay_util
    assert "markLine" in overlay_util
    assert "markPoint" in overlay_util
    assert "全历史" in overlay_util
    assert "近期" in overlay_util
    assert "缩放" in overlay_util or "滑条" in overlay_util

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
