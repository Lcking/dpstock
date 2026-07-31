"""Daily refresh for A-share search snapshot (keeps newly listed names searchable)."""
import threading

from utils.logger import get_logger

logger = get_logger()


class SearchSnapshotScheduler:
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
            logger.info("[SearchSnapshotScheduler] Already running")
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger

            cls._scheduler = BackgroundScheduler()
            # 每个交易日开盘前刷新一次，覆盖前一日新上市股票
            cls._scheduler.add_job(
                cls._run_refresh_job,
                trigger=CronTrigger(
                    day_of_week="mon-fri",
                    hour=8,
                    minute=20,
                    timezone="Asia/Shanghai",
                ),
                id="search_snapshot_daily_job",
                name="Refresh A-share Search Snapshot",
                replace_existing=True,
            )
            cls._scheduler.start()
            cls._running = True
            logger.info(
                "[SearchSnapshotScheduler] Started - weekdays 08:20 Asia/Shanghai"
            )
        except ImportError:
            logger.warning(
                "[SearchSnapshotScheduler] APScheduler not installed, using timer fallback"
            )
            cls._start_simple_timer()
        except Exception as exc:
            logger.error(f"[SearchSnapshotScheduler] Failed to start: {exc}")

    @classmethod
    def _start_simple_timer(cls):
        def run_and_reschedule():
            cls._run_refresh_job()
            timer = threading.Timer(24 * 3600, run_and_reschedule)
            timer.daemon = True
            timer.start()

        timer = threading.Timer(600, run_and_reschedule)
        timer.daemon = True
        timer.start()
        cls._running = True
        logger.info("[SearchSnapshotScheduler] Started (simple timer)")

    @classmethod
    def _run_refresh_job(cls):
        from services.job_health_tracker import job_health_tracker

        job_id = "search_snapshot_scheduler"
        try:
            from services.search_snapshot_service import SearchSnapshotService

            logger.info("[SearchSnapshotScheduler] Refreshing A-share search snapshot...")
            count = SearchSnapshotService().refresh_a_share_snapshot()
            logger.info(f"[SearchSnapshotScheduler] Snapshot rows={count}")
            job_health_tracker.record_success(job_id)
        except Exception as exc:
            logger.error(f"[SearchSnapshotScheduler] Refresh failed: {exc}")
            job_health_tracker.record_failure(job_id, str(exc))


def start_search_snapshot_scheduler():
    SearchSnapshotScheduler.start()
