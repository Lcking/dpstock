import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


def _write_snapshot(snapshot_dir: Path, name: str, rows: list[dict]) -> None:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / name).write_text(
        json.dumps(rows, ensure_ascii=False),
        encoding="utf-8",
    )


def test_search_snapshot_service_reads_local_a_hk_us_snapshots(tmp_path):
    from services.search_snapshot_service import SearchSnapshotService

    _write_snapshot(
        tmp_path,
        "a_shares.json",
        [{"symbol": "600519", "name": "贵州茅台", "market": "A", "pinyin": "gzmt"}],
    )
    _write_snapshot(
        tmp_path,
        "hk_shares.json",
        [{"symbol": "00700", "name": "腾讯控股", "market": "HK", "pinyin": "txkg"}],
    )
    _write_snapshot(
        tmp_path,
        "us_stocks.json",
        [{"symbol": "AAPL", "name": "Apple", "market": "US", "pinyin": "apple"}],
    )

    service = SearchSnapshotService(snapshot_dir=tmp_path)

    assert service.search_a_shares("600") == [{"symbol": "600519", "name": "贵州茅台", "market": "A"}]
    assert service.search_hk_shares("腾讯") == [{"symbol": "00700", "name": "腾讯控股", "market": "HK"}]
    assert service.search_us_stocks("aapl") == [{"symbol": "AAPL", "name": "Apple", "market": "US"}]


def test_search_snapshot_service_returns_direct_a_code_when_snapshot_missing(tmp_path):
    from services.search_snapshot_service import SearchSnapshotService

    service = SearchSnapshotService(snapshot_dir=tmp_path)

    assert service.search_a_shares("600519") == [{"symbol": "600519", "name": "600519", "market": "A"}]


@pytest.mark.asyncio
async def test_search_routes_use_snapshot_service_instead_of_remote_sources(monkeypatch):
    import web_server

    fake_snapshot = MagicMock()
    fake_snapshot.search_a_shares.return_value = [{"symbol": "600519", "name": "贵州茅台", "market": "A"}]
    fake_snapshot.search_hk_shares.return_value = [{"symbol": "00700", "name": "腾讯控股", "market": "HK"}]
    fake_snapshot.search_us_stocks.return_value = [{"symbol": "AAPL", "name": "Apple", "market": "US"}]
    fake_snapshot.search_global.return_value = [
        {"label": "贵州茅台 (600519)", "value": "600519", "market": "A", "name": "贵州茅台"},
        {"label": "腾讯控股 (00700)", "value": "00700", "market": "HK", "name": "腾讯控股"},
        {"label": "Apple (AAPL)", "value": "AAPL", "market": "US", "name": "Apple"},
    ]

    monkeypatch.setattr(web_server, "search_snapshot_service", fake_snapshot)
    monkeypatch.setattr(web_server, "StockAnalyzerService", MagicMock(side_effect=AssertionError("should not build analyzer for search")))
    monkeypatch.setattr(web_server.us_stock_service, "search_us_stocks", AsyncMock(side_effect=AssertionError("should not query us remote service")))

    a_result = await web_server.search_a_shares(keyword="600", username="guest")
    hk_result = await web_server.search_hk_shares(keyword="腾讯", username="guest")
    us_result = await web_server.search_us_stocks(keyword="aapl", username="guest")
    global_result = await web_server.search_global(keyword="a", market_type="ALL", username="guest")

    assert a_result["results"][0]["symbol"] == "600519"
    assert hk_result["results"][0]["symbol"] == "00700"
    assert us_result["results"][0]["symbol"] == "AAPL"
    assert len(global_result["results"]) == 3
