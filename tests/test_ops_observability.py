import sqlite3
from pathlib import Path

import pytest

from database.db_factory import DatabaseFactory
from services.llm_usage_service import LlmUsageService
from services.job_health_tracker import JobHealthTracker
from services.ops_alert_service import OpsAlertService

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = REPO_ROOT / "migrations"


def apply_migrations(db_path: Path, migration_names: list[str]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for migration_name in migration_names:
            sql = (MIGRATIONS_DIR / migration_name).read_text(encoding="utf-8")
            conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def _setup_ops_db(db_path: Path) -> None:
    apply_migrations(db_path, ["002_create_quota_tables.sql", "015_create_ops_tables.sql"])


def test_job_health_tracker_records_success_and_failure(tmp_path):
    db_path = tmp_path / "ops.db"
    _setup_ops_db(db_path)
    DatabaseFactory.initialize(str(db_path))

    tracker = JobHealthTracker()
    tracker.record_success("demo_job")
    tracker.record_failure("demo_job", "boom")
    snapshot = tracker.snapshot()

    assert snapshot["degraded"] is False
    jobs = {job["job_id"]: job for job in snapshot["jobs"]}
    assert jobs["demo_job"]["last_status"] == "fail"
    assert jobs["demo_job"]["consecutive_failures"] == 1


def test_job_health_tracker_marks_degraded_after_threshold(tmp_path):
    db_path = tmp_path / "ops_degraded.db"
    _setup_ops_db(db_path)
    DatabaseFactory.initialize(str(db_path))

    tracker = JobHealthTracker()
    for _ in range(3):
        tracker.record_failure("risk_stock_scheduler", "upstream down")

    snapshot = tracker.snapshot()
    assert snapshot["degraded"] is True
    health = tracker.snapshot_for_health()
    assert health["risk_stock_scheduler"].startswith("fail:")


def test_llm_usage_service_aggregates_by_user_type(tmp_path):
    db_path = tmp_path / "llm_usage.db"
    _setup_ops_db(db_path)
    DatabaseFactory.initialize(str(db_path))

    service = LlmUsageService()
    service.record_analyze(is_authenticated=False, stock_count=2)
    service.record_analyze(is_authenticated=True, stock_count=1)

    summary = service.get_summary(days=7)
    assert summary["totals"]["anonymous"]["call_count"] == 1
    assert summary["totals"]["anonymous"]["stock_count"] == 2
    assert summary["totals"]["authenticated"]["call_count"] == 1
    assert summary["totals"]["authenticated"]["stock_count"] == 1


def test_llm_usage_summary_backfills_from_analysis_records(tmp_path):
    db_path = tmp_path / "llm_usage_history.db"
    apply_migrations(db_path, ["002_create_quota_tables.sql", "008_create_user_tables.sql", "015_create_ops_tables.sql"])
    DatabaseFactory.initialize(str(db_path))

    with DatabaseFactory.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, primary_email, email_verified, profile_completed,
                               is_public_analysis_enabled, status, created_at, last_active_at)
            VALUES ('bound_user', 'bound@example.com', 1, 0, 0, 'active', '2026-06-01', '2026-06-01')
            """
        )
        conn.execute(
            """
            INSERT INTO analysis_records (user_id, stock_code, analysis_date)
            VALUES ('bound_user', '600519.SH', date('now')),
                   ('anon_user', '000001.SZ', date('now')),
                   ('anon_user', '000002.SZ', date('now'))
            """
        )
        conn.commit()

    summary = LlmUsageService().get_summary(days=7)
    assert summary["source"].startswith("analysis_records")
    assert summary["totals"]["authenticated"]["stock_count"] == 1
    assert summary["totals"]["anonymous"]["stock_count"] == 2
    assert summary["totals"]["anonymous"]["call_count"] == 1


def test_ops_alert_service_sends_webhook_on_threshold(monkeypatch):
    sent = []

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout=10):
        sent.append(request.full_url)
        return FakeResponse()

    monkeypatch.setenv("OPS_ALERT_WEBHOOK_URL", "https://example.com/hook")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    service = OpsAlertService()
    service.send_job_failure_alert("verification_scheduler", 3, "timeout")

    assert sent == ["https://example.com/hook"]


def test_health_includes_scheduler_checks(tmp_path, monkeypatch):
    db_path = tmp_path / "health.db"
    _setup_ops_db(db_path)
    DatabaseFactory.initialize(str(db_path))

    from services.job_health_tracker import job_health_tracker

    job_health_tracker.record_success("startup_migrations")

    monkeypatch.setenv("API_URL", "https://example.com/v1")
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("DB_PATH", str(db_path))

    from fastapi.testclient import TestClient
    import web_server

    client = TestClient(web_server.app)
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert "schedulers" in body["checks"]
    assert body["checks"]["schedulers"]["startup_migrations"] == "ok"
    assert body["degraded"] is False


def test_admin_ops_summary_requires_admin_token(tmp_path):
    db_path = tmp_path / "admin_ops.db"
    _setup_ops_db(db_path)
    DatabaseFactory.initialize(str(db_path))

    from fastapi.testclient import TestClient
    import web_server

    client = TestClient(web_server.app)
    response = client.get("/api/admin/ops/summary")
    assert response.status_code == 401
