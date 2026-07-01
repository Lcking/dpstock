"""
Scheduled due-check and digest email for judgment journal records.
"""
from __future__ import annotations

import threading

from utils.logger import get_logger

logger = get_logger()


class JournalDueScheduler:
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
            logger.info("[JournalDueScheduler] Already running")
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger

            cls._scheduler = BackgroundScheduler()
            cls._scheduler.add_job(
                cls._run_job,
                trigger=CronTrigger(hour=9, minute=30, timezone="Asia/Shanghai"),
                id="journal_due_digest_job",
                name="Journal Due Check And Digest Email",
                replace_existing=True,
            )
            cls._scheduler.start()
            cls._running = True
            logger.info("[JournalDueScheduler] Started - daily at 09:30 Asia/Shanghai")
        except ImportError:
            logger.warning("[JournalDueScheduler] APScheduler not installed, using timer fallback")
            cls._start_simple_timer()
        except Exception as exc:
            logger.error(f"[JournalDueScheduler] Failed to start: {exc}")

    @classmethod
    def _start_simple_timer(cls):
        def run_and_reschedule():
            cls._run_job()
            timer = threading.Timer(24 * 3600, run_and_reschedule)
            timer.daemon = True
            timer.start()

        timer = threading.Timer(600, run_and_reschedule)
        timer.daemon = True
        timer.start()
        cls._running = True
        logger.info("[JournalDueScheduler] Started (simple timer)")

    @classmethod
    def _run_job(cls):
        from services.job_health_tracker import job_health_tracker

        job_id = "journal_due_scheduler"
        try:
            from services.journal import journal_service
            from services.journal_due_email_service import JournalDueEmailService

            logger.info("[JournalDueScheduler] Running due check and digest job...")
            updated = journal_service.run_due_check()
            email_result = JournalDueEmailService().send_daily_digests()
            logger.info(
                f"[JournalDueScheduler] due_updated={updated} emails_sent={email_result.get('sent')}"
            )
            job_health_tracker.record_success(job_id)
        except Exception as exc:
            job_health_tracker.record_failure(job_id, str(exc))
            logger.error(f"[JournalDueScheduler] Job failed: {exc}")

    @classmethod
    def trigger_now(cls):
        logger.info("[JournalDueScheduler] Manual trigger requested")
        cls._run_job()


def start_journal_due_scheduler():
    JournalDueScheduler.start()
