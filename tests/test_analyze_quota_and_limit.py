import json
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from database.db_factory import DatabaseFactory
from services.analyze_rate_limiter import reset_analyze_rate_limits
from services.quota_service import QuotaService
from services.user_service import UserService


REPO_ROOT = Path(__file__).resolve().parents[1]


def _apply_migration(db_path: Path, migration_name: str) -> None:
    sql = (REPO_ROOT / "migrations" / migration_name).read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def _setup_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "analyze_quota.db"
    _apply_migration(db_path, "002_create_quota_tables.sql")
    _apply_migration(db_path, "008_create_user_tables.sql")
    DatabaseFactory.initialize(str(db_path))
    return db_path


def _resolve_user_id(db_path: Path, anonymous_id: str) -> str:
    return UserService(db_path=str(db_path)).get_or_create_user_by_identity(
        identity_type="anonymous",
        identity_value=anonymous_id,
    )


def _bind_test_db(monkeypatch, db_path: Path) -> None:
    import auth.dependencies as auth_deps
    import web_server

    monkeypatch.setenv("DB_PATH", str(db_path))
    DatabaseFactory.initialize(str(db_path))
    test_user_service = UserService(db_path=str(db_path))
    monkeypatch.setattr(auth_deps, "_user_service", test_user_service)
    monkeypatch.setattr(web_server, "user_service", test_user_service)
    monkeypatch.setattr("scripts.run_migrations.run_migrations", lambda: None)


def _mock_analyzer(monkeypatch):
    class _DummyAnalyzer:
        def __init__(self):
            self.data_provider = self

        def resolve_stock_code(self, code, market_type="A"):
            return code, code

        async def analyze_stock(self, stock_code, market_type="A", stream=True):
            payload = json.dumps({"stock_code": stock_code, "status": "completed"})
            yield payload

        async def scan_stocks(self, stock_codes, market_type="A", min_score=0, stream=True):
            for code in stock_codes:
                yield json.dumps({"stock_code": code, "status": "completed"})

    import web_server

    monkeypatch.setattr(web_server, "StockAnalyzerService", _DummyAnalyzer)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    reset_analyze_rate_limits()
    yield
    reset_analyze_rate_limits()


def test_analyze_request_rejects_empty_stock_codes(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    _mock_analyzer(monkeypatch)
    from web_server import app

    with TestClient(app) as client:
        response = client.post(
            "/api/analyze",
            json={"stock_codes": [""], "market_type": "A"},
            headers={"X-Anonymous-Id": "anon_empty_code"},
        )

    assert response.status_code == 422


def test_analyze_request_rejects_more_than_batch_max(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    _mock_analyzer(monkeypatch)
    from web_server import app

    codes = [f"{i:06d}" for i in range(21)]
    with TestClient(app) as client:
        response = client.post(
            "/api/analyze",
            json={"stock_codes": codes, "market_type": "A"},
            headers={"X-Anonymous-Id": "anon_batch_limit"},
        )

    assert response.status_code == 422


def test_batch_analysis_consumes_quota_for_each_new_stock(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    _mock_analyzer(monkeypatch)
    from web_server import app

    anonymous_id = "anon_batch_quota"
    user_id = _resolve_user_id(db_path, anonymous_id)
    quota_service = QuotaService(db_path=str(db_path))
    quota_service.record_analysis(user_id, "000001")
    quota_service.record_analysis(user_id, "000002")
    quota_service.record_analysis(user_id, "000003")

    with TestClient(app) as client:
        response = client.post(
            "/api/analyze",
            json={"stock_codes": ["000004", "000005", "000006"], "market_type": "A"},
            headers={"X-Anonymous-Id": anonymous_id},
        )

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "quota_exceeded"
    assert response.json()["detail"]["required_quota"] == 3


def test_batch_analysis_allows_when_quota_is_sufficient(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    _mock_analyzer(monkeypatch)
    from web_server import app

    anonymous_id = "anon_batch_ok"
    user_id = _resolve_user_id(db_path, anonymous_id)
    with TestClient(app) as client:
        response = client.post(
            "/api/analyze",
            json={"stock_codes": ["600519", "000001", "000002"], "market_type": "A"},
            headers={"X-Anonymous-Id": anonymous_id},
        )

    assert response.status_code == 200
    assert "batch" in response.text

    quota_service = QuotaService(db_path=str(db_path))
    status = quota_service.get_quota_status(user_id, is_authenticated=False)
    assert status["used_quota"] == 3
    assert status["remaining_quota"] == 0


def test_analyze_rate_limit_returns_429(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    _mock_analyzer(monkeypatch)
    monkeypatch.setenv("ANALYZE_RATE_LIMIT_PER_MINUTE", "2")
    from services import analyze_rate_limiter

    analyze_rate_limiter._MAX_PER_WINDOW = 2
    from web_server import app

    user_id = "anon_rate_limit"
    headers = {"X-Anonymous-Id": user_id}
    with TestClient(app) as client:
        client.cookies.clear()
        first = client.post(
            "/api/analyze",
            json={"stock_codes": ["600519"], "market_type": "A"},
            headers=headers,
        )
        second = client.post(
            "/api/analyze",
            json={"stock_codes": ["000001"], "market_type": "A"},
            headers=headers,
        )
        third = client.post(
            "/api/analyze",
            json={"stock_codes": ["000002"], "market_type": "A"},
            headers=headers,
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"]["error"] == "rate_limit_minute"


def test_authenticated_user_gets_higher_base_quota(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    quota_service = QuotaService(db_path=str(db_path))

    anon_status = quota_service.get_quota_status("anon_user", is_authenticated=False)
    auth_status = quota_service.get_quota_status("auth_user", is_authenticated=True)

    assert anon_status["base_quota"] == QuotaService.ANONYMOUS_BASE_QUOTA
    assert auth_status["base_quota"] == QuotaService.AUTHENTICATED_BASE_QUOTA
    assert auth_status["total_quota"] > anon_status["total_quota"]
