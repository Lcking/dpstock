"""
Background refresh for the daily risk stock list.
"""
import threading
from datetime import datetime
from typing import Optional

from utils.logger import get_logger

logger = get_logger()


class RiskStockScheduler:
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
            logger.info("[RiskStockScheduler] Already running")
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger

            cls._scheduler = BackgroundScheduler()
            cls._scheduler.add_job(
                cls._run_refresh_job,
                trigger=CronTrigger(hour=16, minute=10, timezone="Asia/Shanghai"),
                id="risk_stock_refresh_job",
                name="Refresh Risk Stock List",
                replace_existing=True,
            )
            cls._scheduler.start()
            cls._running = True
            logger.info("[RiskStockScheduler] Started - daily refresh at 16:10 Asia/Shanghai")
        except ImportError:
            logger.warning("[RiskStockScheduler] APScheduler not installed, using timer fallback")
            cls._start_simple_timer()
        except Exception as exc:
            logger.error(f"[RiskStockScheduler] Failed to start: {exc}")

    @classmethod
    def _start_simple_timer(cls):
        def run_and_reschedule():
            cls._run_refresh_job()
            timer = threading.Timer(24 * 3600, run_and_reschedule)
            timer.daemon = True
            timer.start()

        timer = threading.Timer(300, run_and_reschedule)
        timer.daemon = True
        timer.start()
        cls._running = True
        logger.info("[RiskStockScheduler] Started (simple timer)")

    @classmethod
    def _run_refresh_job(cls):
        try:
            from services.risk_stock_service import RiskStockService

            logger.info("[RiskStockScheduler] Running scheduled risk stock refresh...")
            result = RiskStockService().refresh_daily(source="scheduler")
            logger.info(
                f"[RiskStockScheduler] Completed trade_date={result.get('trade_date')} count={result.get('count')}"
            )
        except Exception as exc:
            logger.error(f"[RiskStockScheduler] Refresh failed: {exc}")

    @classmethod
    def refresh_if_missing(cls, trade_date: Optional[str] = None):
        try:
            from services.risk_stock_service import RiskStockService

            service = RiskStockService()
            latest = service.get_latest_trade_date()
            expected_date = trade_date or service.collector._resolve_trade_date()
            if latest and latest >= expected_date:
                logger.info(
                    f"[RiskStockScheduler] Latest risk stock data already present: {latest} (expected={expected_date})"
                )
                return latest

            result = service.refresh_daily(trade_date=expected_date, source="startup")
            return result.get("trade_date")
        except Exception as exc:
            logger.error(f"[RiskStockScheduler] Startup refresh failed: {exc}")
            return None


def start_risk_stock_scheduler():
    RiskStockScheduler.start()
