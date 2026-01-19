"""
Verification Scheduler Service
Automatically verifies pending judgments on a schedule

Uses APScheduler for background task scheduling
"""
import threading
from datetime import datetime
from typing import List, Dict
from utils.logger import get_logger
from database.db_factory import DatabaseFactory

logger = get_logger()


class VerificationScheduler:
    """
    Scheduled verification service.
    Runs every hour to verify pending judgments automatically.
    """
    
    _instance = None
    _scheduler = None
    _running = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def start(cls, app=None):
        """Start the scheduler"""
        if cls._running:
            logger.info("[VerificationScheduler] Already running")
            return
        
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            
            cls._scheduler = BackgroundScheduler()
            
            # Schedule verification job every hour
            cls._scheduler.add_job(
                cls._run_verification_job,
                trigger=IntervalTrigger(hours=1),
                id='verification_job',
                name='Verify Pending Judgments',
                replace_existing=True
            )
            
            cls._scheduler.start()
            cls._running = True
            logger.info("[VerificationScheduler] Started - will verify pending judgments every hour")
            
        except ImportError:
            logger.warning("[VerificationScheduler] APScheduler not installed. Using simple timer fallback.")
            cls._start_simple_timer()
        except Exception as e:
            logger.error(f"[VerificationScheduler] Failed to start: {e}")
    
    @classmethod
    def _start_simple_timer(cls):
        """Fallback: simple threading timer for environments without APScheduler"""
        def run_and_reschedule():
            cls._run_verification_job()
            # Reschedule for next hour
            timer = threading.Timer(3600, run_and_reschedule)
            timer.daemon = True
            timer.start()
        
        # Run first time after 5 minutes, then every hour
        timer = threading.Timer(300, run_and_reschedule)
        timer.daemon = True
        timer.start()
        cls._running = True
        logger.info("[VerificationScheduler] Started (simple timer) - will verify pending judgments every hour")
    
    @classmethod
    def stop(cls):
        """Stop the scheduler"""
        if cls._scheduler:
            cls._scheduler.shutdown(wait=False)
            cls._running = False
            logger.info("[VerificationScheduler] Stopped")
    
    @classmethod
    def _run_verification_job(cls):
        """Execute the verification job"""
        try:
            logger.info("[VerificationScheduler] Running scheduled verification...")
            
            from services.judgment_service import JudgmentService
            service = JudgmentService()
            
            # Get all unique owner combinations with pending judgments
            pending = cls._get_all_pending_owners()
            
            total_checked = 0
            total_updated = 0
            
            for owner_type, owner_id in pending:
                try:
                    result = service.verify_pending_judgments(
                        owner_type=owner_type,
                        owner_id=owner_id,
                        max_checks=50
                    )
                    total_checked += result.get('checked', 0)
                    total_updated += result.get('updated', 0)
                except Exception as e:
                    logger.error(f"[VerificationScheduler] Failed to verify {owner_type}:{owner_id[:8]}...: {e}")
            
            logger.info(
                f"[VerificationScheduler] Completed - "
                f"owners={len(pending)}, checked={total_checked}, updated={total_updated}"
            )
            
        except Exception as e:
            logger.error(f"[VerificationScheduler] Job failed: {e}")
    
    @classmethod
    def _get_all_pending_owners(cls) -> List[tuple]:
        """Get all unique owner combinations with pending judgments"""
        try:
            rows = DatabaseFactory.fetchall("""
                SELECT DISTINCT owner_type, owner_id 
                FROM judgments 
                WHERE verification_status IS NULL 
                   OR verification_status = 'WAITING'
                LIMIT 100
            """)
            return [(r.get('owner_type'), r.get('owner_id')) for r in rows if r.get('owner_id')]
        except Exception as e:
            logger.error(f"[VerificationScheduler] Failed to get pending owners: {e}")
            return []
    
    @classmethod
    def trigger_now(cls):
        """Manually trigger verification (for testing)"""
        logger.info("[VerificationScheduler] Manual trigger requested")
        cls._run_verification_job()


# Convenience function for startup
def start_verification_scheduler(app=None):
    """Start the verification scheduler"""
    VerificationScheduler.start(app)
