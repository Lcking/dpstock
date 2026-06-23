"""
Weekly judgment recap scheduler — logs recap readiness for observability.
SSR page is rendered on demand from live verifier data.
"""
from __future__ import annotations

import threading

from utils.logger import get_logger

logger = get_logger()


class JudgmentRecapScheduler:
    _instance = None
    _scheduler = None
    _running = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def start(cls):
        if cls._running:
            logger.info("[JudgmentRecapScheduler] Already running")
            return
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger

            cls._scheduler = BackgroundScheduler()
            cls._scheduler.add_job(
                cls._run_weekly_job,
                trigger=CronTrigger(day_of_week="mon", hour=9, minute=0, timezone="Asia/Shanghai"),
                id="judgment_recap_weekly_job",
                name="Weekly Judgment Recap Snapshot",
                replace_existing=True,
            )
            cls._scheduler.start()
            cls._running = True
            logger.info("[JudgmentRecapScheduler] Started - weekly recap Mondays 09:00 Asia/Shanghai")
        except ImportError:
            logger.warning("[JudgmentRecapScheduler] APScheduler not installed, using timer fallback")
            cls._start_simple_timer()
        except Exception as exc:
            logger.error(f"[JudgmentRecapScheduler] Failed to start: {exc}")

    @classmethod
    def _start_simple_timer(cls):
        def run_and_reschedule():
            cls._run_weekly_job()
            timer = threading.Timer(7 * 24 * 3600, run_and_reschedule)
            timer.daemon = True
            timer.start()

        timer = threading.Timer(600, run_and_reschedule)
        timer.daemon = True
        timer.start()
        cls._running = True

    @classmethod
    def _run_weekly_job(cls):
        try:
            from services.judgment_recap_service import JudgmentRecapService

            result = JudgmentRecapService().log_weekly_snapshot(window_days=7)
            logger.info(f"[JudgmentRecapScheduler] Completed {result}")
        except Exception as exc:
            logger.error(f"[JudgmentRecapScheduler] Weekly job failed: {exc}")


def start_judgment_recap_scheduler():
    JudgmentRecapScheduler.start()
