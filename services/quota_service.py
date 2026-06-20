"""
Quota Service
Manages daily analysis quota for anonymous users

REFACTORED: Uses DatabaseFactory for unified database access
"""
import sqlite3
import os
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from utils.logger import get_logger
from database.db_factory import DatabaseFactory

logger = get_logger()


class QuotaService:
    """Service for managing user analysis quota"""
    
    # Constants
    BASE_QUOTA = 5              # Default / authenticated daily quota
    ANONYMOUS_BASE_QUOTA = int(os.getenv("ANALYZE_QUOTA_ANONYMOUS", "3"))
    AUTHENTICATED_BASE_QUOTA = int(os.getenv("ANALYZE_QUOTA_AUTHENTICATED", "5"))
    INVITE_REWARD = 5           # Quota per successful invite
    DAILY_INVITE_LIMIT = 20     # Max invite quota per day
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("DB_PATH", "data/stocks.db")
        self.db = DatabaseFactory  # Use factory for connections
        DatabaseFactory.initialize(self.db_path)
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure quota tables exist (defensive check)"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # Check if analysis_records table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='analysis_records'
                """)
                if not cursor.fetchone():
                    logger.warning("Quota tables not found. Run migration 002.")
        except Exception as e:
            logger.error(f"Failed to check quota tables: {str(e)}")
    
    def _resolve_base_quota(self, is_authenticated: bool = False) -> int:
        if is_authenticated:
            return self.AUTHENTICATED_BASE_QUOTA
        return self.ANONYMOUS_BASE_QUOTA

    def get_quota_status(
        self,
        user_id: str,
        analysis_date: Optional[date] = None,
        *,
        is_authenticated: bool = False,
    ) -> Dict:
        """
        Get comprehensive quota status for a user
        
        Args:
            user_id: Anonymous user ID (aguai_uid)
            analysis_date: Date to check (default: today)
            
        Returns:
            {
                "user_id": str,
                "date": str,
                "base_quota": int,
                "invite_quota": int,
                "total_quota": int,
                "used_quota": int,
                "remaining_quota": int,
                "analyzed_stocks_today": List[str]
            }
        """
        if analysis_date is None:
            analysis_date = date.today()
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get used quota (count of analyses today)
                cursor.execute("""
                    SELECT COUNT(*) as cnt, GROUP_CONCAT(stock_code) as stocks
                    FROM analysis_records
                    WHERE user_id = ? AND analysis_date = ?
                """, (user_id, analysis_date))
                
                result = cursor.fetchone()
                used_quota = result.get('cnt', 0) if result else 0
                stocks_str = result.get('stocks') if result else None
                analyzed_stocks = stocks_str.split(',') if stocks_str else []
                
                # Get invite quota (sum of rewards today, capped at limit)
                cursor.execute("""
                    SELECT COALESCE(SUM(reward_quota), 0) as total
                    FROM invite_rewards
                    WHERE inviter_id = ? AND reward_date = ?
                """, (user_id, analysis_date))
                
                invite_result = cursor.fetchone()
                invite_quota = min(invite_result.get('total', 0) if invite_result else 0, self.DAILY_INVITE_LIMIT)
                
                # Calculate totals
                base_quota = self._resolve_base_quota(is_authenticated)
                total_quota = base_quota + invite_quota
                remaining_quota = max(0, total_quota - used_quota)
                
                return {
                    "user_id": user_id,
                    "date": str(analysis_date),
                    "base_quota": base_quota,
                    "invite_quota": invite_quota,
                    "total_quota": total_quota,
                    "used_quota": used_quota,
                    "remaining_quota": remaining_quota,
                    "analyzed_stocks_today": analyzed_stocks,
                    "is_authenticated": is_authenticated,
                }
                
        except Exception as e:
            logger.error(f"Failed to get quota status: {str(e)}")
            # Return safe defaults on error
            return {
                "user_id": user_id,
                "date": str(analysis_date),
                "base_quota": self._resolve_base_quota(is_authenticated),
                "invite_quota": 0,
                "total_quota": self._resolve_base_quota(is_authenticated),
                "used_quota": 0,
                "remaining_quota": self._resolve_base_quota(is_authenticated),
                "analyzed_stocks_today": [],
                "is_authenticated": is_authenticated,
            }
    
    def check_quota(
        self, 
        user_id: str, 
        stock_code: str, 
        analysis_date: Optional[date] = None,
        *,
        is_authenticated: bool = False,
    ) -> Tuple[bool, str, Dict]:
        """
        Check if user can analyze a stock
        
        Args:
            user_id: Anonymous user ID
            stock_code: Stock code to analyze
            analysis_date: Date to check (default: today)
            
        Returns:
            (allowed: bool, reason: str, details: dict)
            
            reason can be:
            - "history": Already analyzed today (allowed, no quota deduction)
            - "quota_available": New stock, quota available
            - "quota_exceeded": New stock, no quota remaining
        """
        if analysis_date is None:
            analysis_date = date.today()
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if already analyzed today
                cursor.execute("""
                    SELECT id FROM analysis_records
                    WHERE user_id = ? AND stock_code = ? AND analysis_date = ?
                """, (user_id, stock_code, analysis_date))
                
                if cursor.fetchone():
                    return (True, "history", {
                        "message": "这是您今日已分析过的股票,可以重复查看"
                    })
                
                # Get quota status
                status = self.get_quota_status(
                    user_id,
                    analysis_date,
                    is_authenticated=is_authenticated,
                )
                
                if status["remaining_quota"] > 0:
                    return (True, "quota_available", {
                        "remaining_quota": status["remaining_quota"],
                        "message": f"可以分析,剩余 {status['remaining_quota']} 次新股票额度"
                    })
                else:
                    return (False, "quota_exceeded", {
                        "remaining_quota": 0,
                        "total_quota": status["total_quota"],
                        "analyzed_stocks_today": status["analyzed_stocks_today"],
                        "message": self._get_quota_exceeded_message(status)
                    })
                    
        except Exception as e:
            logger.error(f"Failed to check quota: {str(e)}")
            # Fail open: allow analysis on error
            return (True, "error_fallback", {
                "message": "额度检查失败,允许分析"
            })

    def check_quota_for_codes(
        self,
        user_id: str,
        stock_codes: List[str],
        analysis_date: Optional[date] = None,
        *,
        is_authenticated: bool = False,
    ) -> Tuple[bool, str, Dict]:
        """Check whether the user can analyze all requested codes (batch-aware)."""
        if analysis_date is None:
            analysis_date = date.today()

        codes = list(dict.fromkeys(str(code).strip() for code in stock_codes if str(code).strip()))
        if not codes:
            return (False, "invalid_request", {"message": "请输入代码"})

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                new_codes: List[str] = []
                history_codes: List[str] = []

                for code in codes:
                    cursor.execute(
                        """
                        SELECT id FROM analysis_records
                        WHERE user_id = ? AND stock_code = ? AND analysis_date = ?
                        """,
                        (user_id, code, analysis_date),
                    )
                    if cursor.fetchone():
                        history_codes.append(code)
                    else:
                        new_codes.append(code)

            status = self.get_quota_status(
                user_id,
                analysis_date,
                is_authenticated=is_authenticated,
            )
            required = len(new_codes)
            remaining = status["remaining_quota"]

            if required <= remaining:
                return (
                    True,
                    "quota_available",
                    {
                        "remaining_quota": remaining,
                        "required_quota": required,
                        "new_codes": new_codes,
                        "history_codes": history_codes,
                        "message": (
                            f"可以分析 {len(codes)} 只标的，其中 {required} 只需新额度"
                            if required
                            else "均为今日已分析标的，可重复查看"
                        ),
                    },
                )

            return (
                False,
                "quota_exceeded",
                {
                    "remaining_quota": remaining,
                    "required_quota": required,
                    "new_codes": new_codes,
                    "history_codes": history_codes,
                    "total_quota": status["total_quota"],
                    "analyzed_stocks_today": status["analyzed_stocks_today"],
                    "message": self._get_quota_exceeded_message(status),
                },
            )
        except Exception as e:
            logger.error(f"Failed to check batch quota: {str(e)}")
            return (True, "error_fallback", {"message": "额度检查失败,允许分析"})

    def record_analyses(
        self,
        user_id: str,
        stock_codes: List[str],
        analysis_date: Optional[date] = None,
    ) -> int:
        recorded = 0
        for code in dict.fromkeys(str(item).strip() for item in stock_codes if str(item).strip()):
            if self.record_analysis(user_id, code, analysis_date):
                recorded += 1
        return recorded
    
    def record_analysis(
        self, 
        user_id: str, 
        stock_code: str, 
        analysis_date: Optional[date] = None
    ) -> bool:
        """
        Record an analysis (consumes quota)
        
        Args:
            user_id: Anonymous user ID
            stock_code: Stock code analyzed
            analysis_date: Date of analysis (default: today)
            
        Returns:
            True if recorded successfully
        """
        if analysis_date is None:
            analysis_date = date.today()
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO analysis_records 
                    (user_id, stock_code, analysis_date)
                    VALUES (?, ?, ?)
                """, (user_id, stock_code, analysis_date))
                conn.commit()
                
                logger.info(f"Recorded analysis: user={user_id}, stock={stock_code}, date={analysis_date}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to record analysis: {str(e)}")
            return False
    
    def _get_quota_exceeded_message(self, status: Dict) -> str:
        """Generate friendly quota exceeded message"""
        analyzed = status.get("analyzed_stocks_today", [])
        total = status.get("total_quota", self.BASE_QUOTA)
        
        message = f"今日新股票分析次数已用完 ({total}/{total})\n\n"
        message += "💡 建议：\n"
        
        if analyzed:
            message += f"- 重新查看今日已分析的 {len(analyzed)} 支股票,深化判断\n"
        
        message += "- 邀请朋友使用,解锁更多额度\n"
        message += "- 明日额度将自动恢复\n\n"
        message += "💡 提示：专注少数标的,比广撒网更有价值"
        
        return message
