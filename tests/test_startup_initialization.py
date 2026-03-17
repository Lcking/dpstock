import asyncio
import sqlite3
import sys
import importlib
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import pandas as pd

from services.ai_analyzer import AIAnalyzer
from services.judgment_service import JudgmentService
from services.stock_data_provider import StockDataProvider
from services.us_stock_service_async import USStockServiceAsync
from services.tushare.client import TushareClient


def _apply_migration(db_path: Path, migration_name: str) -> None:
    migration_path = Path(__file__).resolve().parents[1] / "migrations" / migration_name
    sql = migration_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def test_tushare_client_can_initialize_after_token_appears(monkeypatch):
    TushareClient._instance = None
    TushareClient._pro = None
    TushareClient._initialized = False

    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    client = TushareClient()
    assert client.is_available is False

    mock_pro = MagicMock()
    mock_ts = MagicMock()
    mock_ts.pro_api.return_value = mock_pro
    monkeypatch.setenv("TUSHARE_TOKEN", "test-token")
    monkeypatch.setattr("services.tushare.client.ts", mock_ts)

    client.ensure_initialized()

    mock_ts.set_token.assert_called_once_with("test-token")
    mock_ts.pro_api.assert_called_once()
    assert client.is_available is True


def test_judgment_service_initializes_legacy_schema_without_error(tmp_path):
    db_path = tmp_path / "legacy.db"
    _apply_migration(db_path, "001_create_judgments_tables.sql")

    service = JudgmentService(db_path=str(db_path))
    assert service is not None

    conn = sqlite3.connect(db_path)
    try:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(judgments)").fetchall()
        }
    finally:
        conn.close()

    assert "verification_period" in columns


def test_importing_judgments_route_does_not_construct_service_eagerly(monkeypatch):
    class _ShouldNotInstantiate:
        def __init__(self, *args, **kwargs):
            raise AssertionError("JudgmentService should not be instantiated during import")

    monkeypatch.setattr("services.judgment_service.JudgmentService", _ShouldNotInstantiate)
    sys.modules.pop("routes.judgments", None)

    module = importlib.import_module("routes.judgments")

    assert hasattr(module, "get_actor")


def test_importing_admin_route_does_not_construct_service_eagerly(monkeypatch):
    class _ShouldNotInstantiate:
        def __init__(self, *args, **kwargs):
            raise AssertionError("AdminService should not be instantiated during import")

    monkeypatch.setattr("services.admin_service.AdminService", _ShouldNotInstantiate)
    sys.modules.pop("routes.admin", None)

    module = importlib.import_module("routes.admin")

    assert hasattr(module, "verify_admin_token")


def test_importing_web_server_has_no_startup_info_noise():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", "import web_server; print('ok')"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout + result.stderr
    assert "[AdminService] Using DB path" not in output
    assert "前端构建目录挂载成功" not in output
    assert "ok" in output


def test_lookup_stock_name_does_not_call_tushare_on_cache_miss(monkeypatch):
    StockDataProvider._shared_a_share_list_cache = None
    provider = StockDataProvider()

    namechange = MagicMock(return_value=None)
    fake_tushare = SimpleNamespace(
        is_available=True,
        pro=SimpleNamespace(namechange=namechange),
    )
    monkeypatch.setattr("services.tushare.client.tushare_client", fake_tushare)

    assert provider.lookup_stock_name("600519") == ""
    namechange.assert_not_called()


def test_get_a_share_list_initializes_tushare_before_fallback(monkeypatch):
    StockDataProvider._shared_a_share_list_cache = None
    provider = StockDataProvider()

    class _FakeTushareClient:
        def __init__(self):
            self.pro = None
            self.is_available = False
            self.ensure_initialized_called = False

        def ensure_initialized(self, log_missing_token: bool = False):
            self.ensure_initialized_called = True
            self.is_available = True
            self.pro = SimpleNamespace(
                stock_basic=lambda **kwargs: pd.DataFrame(
                    [{"ts_code": "600519.SH", "name": "贵州茅台"}]
                )
            )

    fake_tushare = _FakeTushareClient()

    monkeypatch.setattr("services.stock_data_provider.tushare_client", fake_tushare)
    monkeypatch.setitem(sys.modules, "akshare", SimpleNamespace(stock_info_a_code_name=lambda: (_ for _ in ()).throw(RuntimeError("akshare down"))))

    rows = provider.get_a_share_list()

    assert fake_tushare.ensure_initialized_called is True
    assert rows[0]["code"] == "600519"
    assert rows[0]["name"] == "贵州茅台"


def test_prod_compose_exports_tushare_token():
    repo_root = Path(__file__).resolve().parents[1]
    compose_text = (repo_root / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "- TUSHARE_TOKEN=${TUSHARE_TOKEN}" in compose_text


def test_nginx_http_healthcheck_matches_config():
    repo_root = Path(__file__).resolve().parents[1]
    compose_text = (repo_root / "docker-compose.prod.yml").read_text(encoding="utf-8")
    nginx_text = (repo_root / "nginx/nginx.conf").read_text(encoding="utf-8")

    assert 'http://localhost/health' in compose_text
    assert 'location = /health' in nginx_text
    http_server_block = nginx_text.split('# HTTPS服务器', 1)[0]
    assert 'return 200 "healthy\\n";' in http_server_block


@pytest.mark.asyncio
async def test_search_global_returns_partial_results_when_us_search_times_out(monkeypatch):
    import web_server

    class _DummyProvider:
        def lookup_stock_name(self, stock_code: str, allow_network: bool = False):
            return "贵州茅台"

        def get_a_share_list(self):
            return [{"code": "600519", "name": "贵州茅台", "pinyin": "gzmt"}]

        def get_hk_share_list(self):
            return []

    class _DummyAnalyzer:
        def __init__(self):
            self.data_provider = _DummyProvider()

    async def _slow_us_search(keyword: str):
        await asyncio.sleep(0.05)
        return [{"symbol": "AAPL", "name": "Apple"}]

    monkeypatch.setattr(web_server, "SEARCH_TASK_TIMEOUT_SECONDS", 0.01, raising=False)
    monkeypatch.setattr(web_server, "StockAnalyzerService", _DummyAnalyzer)
    monkeypatch.setattr(web_server.us_stock_service, "search_us_stocks", _slow_us_search)

    result = await web_server.search_global(keyword="600519", market_type="ALL", username="guest")

    assert result["results"]
    assert result["results"][0]["value"] == "600519"
    assert all(item["market"] != "US" for item in result["results"])


@pytest.mark.asyncio
async def test_us_search_uses_local_catalog_without_remote_fetch(monkeypatch):
    service = USStockServiceAsync()
    get_info = MagicMock(side_effect=AssertionError("search should not fetch remote ticker info"))
    monkeypatch.setattr(service, "_get_stock_info", get_info)

    results = await service.search_us_stocks("aapl")

    assert any(item["symbol"] == "AAPL" for item in results)
    get_info.assert_not_called()


@pytest.mark.asyncio
async def test_ai_score_timeout_degrades_without_blocking():
    analyzer = AIAnalyzer()

    class _SlowCalculator:
        def calculate(self, **kwargs):
            import time
            time.sleep(0.05)
            return {"score": 1}

    analyzer.ai_score_calc = _SlowCalculator()
    analyzer.AI_SCORE_TIMEOUT = 0.01

    result = await analyzer._calculate_ai_score_with_timeout(
        df=None,
        stock_code="600519",
        market_type="A",
        analysis_v1=None,
    )

    assert result is None
