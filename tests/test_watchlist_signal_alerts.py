"""观察池结构信号扫描：信号检测、入库去重、inbox 聚合、前端契约。"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from database.db_factory import DatabaseFactory
from services.watchlist_signal_service import WatchlistSignalService

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = REPO_ROOT / "migrations"


def _apply_migrations(db_path: Path, names: list) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for name in names:
            conn.executescript((MIGRATIONS_DIR / name).read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def _recent_df(closes: list, volumes: list) -> pd.DataFrame:
    """构造以今天为最后一根 bar 的日线 DataFrame。"""
    rows = len(closes)
    end = datetime.now()
    dates = pd.bdate_range(end=end, periods=rows)
    return pd.DataFrame(
        {
            "Open": closes,
            "Close": closes,
            "High": [c * 1.01 for c in closes],
            "Low": [c * 0.99 for c in closes],
            "Volume": volumes,
        },
        index=dates,
    )


def test_detect_golden_cross_signal():
    # V 型反转序列，截取到 MA5 首次上穿 MA20 的那根 bar
    full = list(np.linspace(112, 100, 22)) + list(np.linspace(101, 118, 12))
    series = pd.Series(full)
    ma5 = series.rolling(5).mean()
    ma20 = series.rolling(20).mean()
    cross_idx = None
    for i in range(21, len(full)):
        if ma5[i - 1] <= ma20[i - 1] and ma5[i] > ma20[i]:
            cross_idx = i
            break
    assert cross_idx is not None, "测试数据未产生金叉"

    closes = full[: cross_idx + 1]
    volumes = [1_000_000.0] * len(closes)
    df = _recent_df(closes, volumes)

    signals = WatchlistSignalService().detect_signals(df)
    types = {s["signal_type"] for s in signals}
    assert "golden_cross" in types
    signal = next(s for s in signals if s["signal_type"] == "golden_cross")
    assert "不构成投资建议" in signal["detail"]
    assert signal["trade_date"] == df.index[-1].strftime("%Y-%m-%d")


def test_detect_ma20_breakout_with_volume():
    # 长期横盘在 MA20 下方，最后一天放量突破
    closes = [100.0] * 29 + [104.0]
    volumes = [1_000_000.0] * 29 + [2_000_000.0]
    df = _recent_df(closes, volumes)

    signals = WatchlistSignalService().detect_signals(df)
    types = {s["signal_type"] for s in signals}
    assert "ma20_breakout_up" in types


def test_detect_volume_spike():
    closes = [100.0] * 29 + [103.0]
    volumes = [1_000_000.0] * 29 + [3_000_000.0]
    df = _recent_df(closes, volumes)

    signals = WatchlistSignalService().detect_signals(df)
    types = {s["signal_type"] for s in signals}
    assert "volume_spike" in types


def test_no_signal_on_flat_data():
    closes = [100.0] * 30
    volumes = [1_000_000.0] * 30
    df = _recent_df(closes, volumes)

    signals = WatchlistSignalService().detect_signals(df)
    assert signals == []


def test_stale_data_produces_no_signal():
    closes = list(np.linspace(110, 100, 25)) + [104.0, 108.0, 112.0, 116.0, 120.0]
    volumes = [1_000_000.0] * len(closes)
    old_end = datetime.now() - timedelta(days=30)
    dates = pd.bdate_range(end=old_end, periods=len(closes))
    df = pd.DataFrame(
        {"Open": closes, "Close": closes, "High": closes, "Low": closes, "Volume": volumes},
        index=dates,
    )

    assert WatchlistSignalService().detect_signals(df) == []


def test_scan_and_sync_creates_deduped_alerts(tmp_path, monkeypatch):
    db_path = tmp_path / "signal_alerts.db"
    _apply_migrations(db_path, [
        "004_create_watchlist_tables.sql",
        "017_create_watchlist_signal_alerts.sql",
    ])
    DatabaseFactory.initialize(str(db_path))

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO watchlists (id, user_id, name, created_at, updated_at) "
            "VALUES ('wl1', 'u1', '默认', '2026-01-01', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO watchlist_items (watchlist_id, ts_code, name, added_at) "
            "VALUES ('wl1', '600519.SH', '贵州茅台', '2026-01-01')"
        )
        conn.commit()

    service = WatchlistSignalService()

    fake_signal = {
        "signal_type": "golden_cross",
        "title": "MA5 上穿 MA20（金叉）",
        "detail": "测试信号。该信号为结构观察提示，不构成投资建议。",
        "trade_date": "2026-07-07",
    }
    monkeypatch.setattr(
        service,
        "_scan_symbols",
        lambda codes: {"600519.SH": [fake_signal]},
    )

    first = service.scan_and_sync()
    assert first["created"] == 1
    assert first["matched_users"] == 1

    # 再跑一次：同一 (user, code, date, type) 不重复
    second = service.scan_and_sync()
    assert second["created"] == 0

    assert service.get_unread_count("u1") == 1
    alerts = service.list_alerts("u1")
    assert alerts["items"][0]["stock_name"] == "贵州茅台"
    assert alerts["items"][0]["signal_type"] == "golden_cross"

    service.mark_all_read("u1")
    assert service.get_unread_count("u1") == 0


def test_notification_inbox_includes_signal_alerts():
    from fastapi.testclient import TestClient

    from web_server import app

    with TestClient(app) as client:
        response = client.get("/api/v1/notifications/inbox")

    assert response.status_code == 200
    data = response.json()
    assert "signal_alert_count" in data
    assert "signal_preview" in data


def test_signal_alert_routes_registered():
    from fastapi.testclient import TestClient

    from web_server import app

    with TestClient(app) as client:
        listing = client.get("/api/watchlists/signal-alerts")
        assert listing.status_code == 200
        assert "items" in listing.json()

        marked = client.post("/api/watchlists/signal-alerts/mark-read")
        assert marked.status_code == 200


def test_frontend_watchlist_page_renders_signal_panel():
    watchlist_text = (REPO_ROOT / "frontend/src/components/Watchlist/WatchlistList.vue").read_text(encoding="utf-8")
    assert "signal-alert-panel" in watchlist_text
    assert "自选结构信号" in watchlist_text
    assert "markSignalAlertsRead" in watchlist_text
    assert "focus === 'signals'" in watchlist_text.replace('"', "'")

    nav_text = (REPO_ROOT / "frontend/src/components/NavBar.vue").read_text(encoding="utf-8")
    assert "signalAlertCount" in nav_text
    assert "focus=signals" in nav_text

    store_text = (REPO_ROOT / "frontend/src/stores/notification.ts").read_text(encoding="utf-8")
    assert "signalAlertCount" in store_text
    assert "signal_alert_count" in store_text
