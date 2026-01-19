from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from services.database_service import DatabaseService
from utils.logger import get_logger

logger = get_logger()

class AdminService:
    """
    Service for administrative overview and statistics.
    """
    
    def __init__(self):
        self.db = DatabaseService()

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get global system statistics.
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Total Bound Emails (Anchors)
                cursor.execute("SELECT count(*) FROM anchors WHERE anchor_type = 'email'")
                total_anchors = cursor.fetchone()[0]
                
                # 2. Total Judgments
                cursor.execute("SELECT count(*) FROM judgments")
                total_judgments = cursor.fetchone()[0]
                
                # 3. Recent Bound Emails (Last 24h)
                yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                cursor.execute("SELECT count(*) FROM anchors WHERE anchor_type = 'email' AND created_at > ?", (yesterday,))
                recent_anchors = cursor.fetchone()[0]
                
                # 4. Success Rates (Confirmed vs Total)
                cursor.execute("SELECT count(*) FROM judgments WHERE verification_status = 'CONFIRMED'")
                confirmed_judgments = cursor.fetchone()[0]
                
                return {
                    "total_anchors": total_anchors,
                    "total_judgments": total_judgments,
                    "recent_anchors_24h": recent_anchors,
                    "confirmed_judgments": confirmed_judgments,
                    "server_time": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {}

    def get_registered_users(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get list of registered users (anchors) with masked emails.
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT anchor_id, anchor_value_masked, created_at 
                    FROM anchors 
                    WHERE anchor_type = 'email'
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                users = []
                for row in rows:
                    users.append({
                        "anchor_id": row[0],
                        "email": row[1],
                        "created_at": row[2]
                    })
                return users
        except Exception as e:
            logger.error(f"Failed to get registered users: {e}")
            return []
