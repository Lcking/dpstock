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
    from services import analyze_rate_limiter

    original_window = analyze_rate_limiter._MAX_PER_WINDOW
    original_daily = analyze_rate_limiter._DAILY_MAX
    reset_analyze_rate_limits()
    yield
    analyze_rate_limiter._MAX_PER_WINDOW = original_window
    analyze_rate_limiter._DAILY_MAX = original_daily
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

    headers = {"X-Real-IP": "203.0.113.10", "X-Anonymous-Id": "anon_batch_quota"}
    with TestClient(app) as client:
        first = client.post(
            "/api/analyze",
            json={"stock_codes": ["000001", "000002", "000003"], "market_type": "A"},
            headers=headers,
        )
        rotated = client.post(
            "/api/analyze",
            json={"stock_codes": ["000004", "000005", "000006"], "market_type": "A"},
            headers={"X-Real-IP": "203.0.113.10", "X-Anonymous-Id": "anon_batch_quota_rotated"},
        )

    assert first.status_code == 200
    assert rotated.status_code == 403
    assert rotated.json()["detail"]["error"] == "quota_exceeded"
    assert rotated.json()["detail"]["required_quota"] == 3


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


def test_anonymous_quota_status_follows_real_ip(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    _mock_analyzer(monkeypatch)
    from web_server import app

    ip_headers = {"X-Real-IP": "203.0.113.20"}
    with TestClient(app) as client:
        analyzed = client.post(
            "/api/analyze",
            json={"stock_codes": ["600519"], "market_type": "A"},
            headers={**ip_headers, "X-Anonymous-Id": "anon_status_a"},
        )
        status = client.get(
            "/api/v1/quota/status",
            headers={**ip_headers, "X-Anonymous-Id": "anon_status_b"},
        )

    assert analyzed.status_code == 200
    body = status.json()
    assert body["used_quota"] == 1
    assert body["remaining_quota"] == body["total_quota"] - 1
    assert "600519" in body["analyzed_stocks_today"]


def test_global_daily_cap_stops_model_calls(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    _mock_analyzer(monkeypatch)
    monkeypatch.setenv("ANALYZE_GLOBAL_DAILY_MAX", "1")
    from web_server import app

    with TestClient(app) as client:
        first = client.post(
            "/api/analyze",
            json={"stock_codes": ["600519"], "market_type": "A"},
            headers={"X-Real-IP": "203.0.113.31", "X-Anonymous-Id": "anon_global_a"},
        )
        second = client.post(
            "/api/analyze",
            json={"stock_codes": ["000001"], "market_type": "A"},
            headers={"X-Real-IP": "203.0.113.32", "X-Anonymous-Id": "anon_global_b"},
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["error"] == "global_daily_exceeded"


def test_global_daily_cap_persists_across_guard_instances(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("ANALYZE_GLOBAL_DAILY_MAX", "1")
    from services.analyze_spend_guard import AnalyzeSpendGuard

    first = AnalyzeSpendGuard(db_path=str(db_path)).reserve(
        client_ip="203.0.113.40",
        stock_codes=["600519"],
        enforce_ip_quota=False,
    )
    second = AnalyzeSpendGuard(db_path=str(db_path)).reserve(
        client_ip="203.0.113.41",
        stock_codes=["000001"],
        enforce_ip_quota=False,
    )

    assert first[0] is True
    assert second[0] is False
    assert second[1] == "global_daily_exceeded"


def test_repeat_view_does_not_consume_another_ip_slot(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    _mock_analyzer(monkeypatch)
    monkeypatch.setenv("ANALYZE_QUOTA_ANONYMOUS", "1")
    from web_server import app

    headers = {"X-Real-IP": "203.0.113.50", "X-Anonymous-Id": "anon_repeat"}
    with TestClient(app) as client:
        first = client.post(
            "/api/analyze",
            json={"stock_codes": ["600519"], "market_type": "A"},
            headers=headers,
        )
        repeat = client.post(
            "/api/analyze",
            json={"stock_codes": ["600519"], "market_type": "A"},
            headers=headers,
        )
        fresh = client.post(
            "/api/analyze",
            json={"stock_codes": ["000001"], "market_type": "A"},
            headers=headers,
        )

    assert first.status_code == 200
    assert repeat.status_code == 200
    assert fresh.status_code == 403
    assert fresh.json()["detail"]["error"] == "quota_exceeded"


def test_minute_limit_is_shared_by_ip_across_anonymous_ids(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    _mock_analyzer(monkeypatch)
    from services import analyze_rate_limiter

    analyze_rate_limiter._MAX_PER_WINDOW = 1
    from web_server import app

    with TestClient(app) as client:
        first = client.post(
            "/api/analyze",
            json={"stock_codes": ["600519"], "market_type": "A"},
            headers={"X-Real-IP": "203.0.113.60", "X-Anonymous-Id": "anon_rate_a"},
        )
        second = client.post(
            "/api/analyze",
            json={"stock_codes": ["000001"], "market_type": "A"},
            headers={"X-Real-IP": "203.0.113.60", "X-Anonymous-Id": "anon_rate_b"},
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["error"] == "rate_limit_minute"


def test_frontend_explains_ip_quota_and_global_limit():
    quota_status = (REPO_ROOT / "frontend/src/components/QuotaStatus.vue").read_text(encoding="utf-8")
    analyze_app = (REPO_ROOT / "frontend/src/components/StockAnalysisApp.vue").read_text(encoding="utf-8")
    assert "未登录时按当前网络计次" in quota_status
    assert "response.status === 429" in analyze_app
    assert "detailMessage" in analyze_app


def test_authenticated_user_gets_higher_base_quota(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    _bind_test_db(monkeypatch, db_path)
    quota_service = QuotaService(db_path=str(db_path))

    anon_status = quota_service.get_quota_status("anon_user", is_authenticated=False)
    auth_status = quota_service.get_quota_status("auth_user", is_authenticated=True)

    assert anon_status["base_quota"] == QuotaService.ANONYMOUS_BASE_QUOTA
    assert auth_status["base_quota"] == QuotaService.AUTHENTICATED_BASE_QUOTA
    assert auth_status["total_quota"] > anon_status["total_quota"]
