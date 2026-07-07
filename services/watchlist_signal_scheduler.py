"""
Background scheduler for watchlist structure signal scanning.
盘后 16:40（上海时区）扫描观察池标的，生成结构信号站内提醒。
"""
from utils.logger import get_logger

logger = get_logger()


class WatchlistSignalScheduler:
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
            logger.info("[WatchlistSignalScheduler] Already running")
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger

            cls._scheduler = BackgroundScheduler()
            cls._scheduler.add_job(
                cls._run_scan_job,
                trigger=CronTrigger(hour=16, minute=40, timezone="Asia/Shanghai"),
                id="watchlist_signal_scan_job",
                name="Scan Watchlist Structure Signals",
                replace_existing=True,
            )
            cls._scheduler.start()
            cls._running = True
            logger.info("[WatchlistSignalScheduler] Started - daily scan at 16:40 Asia/Shanghai")
        except Exception as exc:
            logger.error(f"[WatchlistSignalScheduler] Failed to start: {exc}")

    @classmethod
    def _run_scan_job(cls):
        from services.job_health_tracker import job_health_tracker

        job_id = "watchlist_signal_scheduler"
        try:
            from services.watchlist_signal_service import WatchlistSignalService

            logger.info("[WatchlistSignalScheduler] Running scheduled signal scan...")
            result = WatchlistSignalService().scan_and_sync()
            logger.info(f"[WatchlistSignalScheduler] Completed {result}")
            job_health_tracker.record_success(job_id)
        except Exception as exc:
            job_health_tracker.record_failure(job_id, str(exc))
            logger.error(f"[WatchlistSignalScheduler] Scan failed: {exc}")


def start_watchlist_signal_scheduler():
    WatchlistSignalScheduler.start()
