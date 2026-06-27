"""
Track background job / startup task health for ops and /api/health.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from database.db_factory import DatabaseFactory
from utils.logger import get_logger

logger = get_logger()

_FAILURE_ALERT_THRESHOLD = int(__import__("os").getenv("OPS_ALERT_FAILURE_THRESHOLD", "3"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"


class JobHealthTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memory: Dict[str, Dict[str, Any]] = {}

    def _ensure_table(self, cursor) -> bool:
        row = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='job_health'"
        ).fetchone()
        return bool(row)

    def ensure_registered(self, job_id: str, *, detail: str = "awaiting first run") -> None:
        self._load_from_db()
        with self._lock:
            if job_id in self._memory:
                return
            self._memory[job_id] = {
                "job_id": job_id,
                "last_run_at": None,
                "last_success_at": None,
                "last_status": "scheduled",
                "last_error": detail,
                "consecutive_failures": 0,
            }
        self._persist(job_id)

    def record_success(self, job_id: str, *, detail: str = "") -> None:
        now = _utc_now()
        with self._lock:
            self._memory[job_id] = {
                "job_id": job_id,
                "last_run_at": now,
                "last_success_at": now,
                "last_status": "ok",
                "last_error": detail or None,
                "consecutive_failures": 0,
            }
        self._persist(job_id)

    def record_failure(self, job_id: str, error: str) -> None:
        now = _utc_now()
        failures = 1
        with self._lock:
            prev = self._memory.get(job_id, {})
            if prev.get("last_status") == "fail":
                failures = int(prev.get("consecutive_failures") or 0) + 1
            self._memory[job_id] = {
                "job_id": job_id,
                "last_run_at": now,
                "last_success_at": prev.get("last_success_at"),
                "last_status": "fail",
                "last_error": (error or "")[:500],
                "consecutive_failures": failures,
            }
            snapshot = dict(self._memory[job_id])
        self._persist(job_id)
        if failures == _FAILURE_ALERT_THRESHOLD:
            from services.ops_alert_service import ops_alert_service

            ops_alert_service.send_job_failure_alert(job_id, failures, snapshot.get("last_error") or "")

    def _persist(self, job_id: str) -> None:
        row = self._memory.get(job_id)
        if not row:
            return
        try:
            with DatabaseFactory.get_connection() as conn:
                cursor = conn.cursor()
                if not self._ensure_table(cursor):
                    return
                cursor.execute(
                    """
                    INSERT INTO job_health (
                        job_id, last_run_at, last_success_at, last_status,
                        last_error, consecutive_failures, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(job_id) DO UPDATE SET
                        last_run_at = excluded.last_run_at,
                        last_success_at = excluded.last_success_at,
                        last_status = excluded.last_status,
                        last_error = excluded.last_error,
                        consecutive_failures = excluded.consecutive_failures,
                        updated_at = excluded.updated_at
                    """,
                    (
                        job_id,
                        row.get("last_run_at"),
                        row.get("last_success_at"),
                        row.get("last_status"),
                        row.get("last_error"),
                        int(row.get("consecutive_failures") or 0),
                        _utc_now(),
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.warning(f"[JobHealth] Persist skipped for {job_id}: {exc}")

    def _load_from_db(self) -> None:
        try:
            with DatabaseFactory.get_connection() as conn:
                cursor = conn.cursor()
                if not self._ensure_table(cursor):
                    return
                rows = cursor.execute(
                    """
                    SELECT job_id, last_run_at, last_success_at, last_status,
                           last_error, consecutive_failures
                    FROM job_health
                    """
                ).fetchall()
            with self._lock:
                for row in rows or []:
                    job_id = row.get("job_id")
                    if job_id:
                        self._memory[job_id] = dict(row)
        except Exception as exc:
            logger.warning(f"[JobHealth] Load skipped: {exc}")

    def snapshot(self) -> Dict[str, Any]:
        self._load_from_db()
        with self._lock:
            jobs = sorted(self._memory.values(), key=lambda item: item.get("job_id") or "")
        degraded = any(int(job.get("consecutive_failures") or 0) >= _FAILURE_ALERT_THRESHOLD for job in jobs)
        return {
            "failure_alert_threshold": _FAILURE_ALERT_THRESHOLD,
            "degraded": degraded,
            "jobs": jobs,
        }

    def snapshot_for_health(self) -> Dict[str, str]:
        data = self.snapshot()
        checks: Dict[str, str] = {}
        for job in data.get("jobs") or []:
            job_id = job.get("job_id") or "unknown"
            failures = int(job.get("consecutive_failures") or 0)
            status = job.get("last_status") or "unknown"
            if failures >= _FAILURE_ALERT_THRESHOLD:
                checks[job_id] = f"fail: {failures} consecutive"
            elif status == "fail":
                checks[job_id] = f"degraded: last run failed"
            elif status == "scheduled":
                checks[job_id] = "scheduled"
            else:
                checks[job_id] = "ok"
        return checks

    def is_degraded(self) -> bool:
        return bool(self.snapshot().get("degraded"))


job_health_tracker = JobHealthTracker()


def track_job(job_id: str):
    """Decorator for scheduler / background callables."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                job_health_tracker.record_success(job_id)
                return result
            except Exception as exc:
                job_health_tracker.record_failure(job_id, str(exc))
                raise

        wrapper.__name__ = getattr(func, "__name__", job_id)
        return wrapper

    return decorator
