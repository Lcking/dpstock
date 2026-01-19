from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from database.db_factory import DatabaseFactory
from utils.logger import get_logger

logger = get_logger()

class AdminService:
    """
    Service for administrative overview and statistics.
    """
    
    def __init__(self):
        self.db = DatabaseFactory()

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get global system statistics.
        """
        try:
            # 1. Total Bound Emails (Anchors)
            total_anchors_row = self.db.fetchone("SELECT count(*) as total FROM anchors WHERE anchor_type = 'email'")
            total_anchors = total_anchors_row.get('total', 0) if total_anchors_row else 0
            
            # 2. Total Judgments
            total_judgments_row = self.db.fetchone("SELECT count(*) as total FROM judgments")
            total_judgments = total_judgments_row.get('total', 0) if total_judgments_row else 0
            
            # 3. Recent Bound Emails (Last 24h)
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            recent_anchors_row = self.db.fetchone(
                "SELECT count(*) as total FROM anchors WHERE anchor_type = 'email' AND created_at > ?", 
                (yesterday,)
            )
            recent_anchors = recent_anchors_row.get('total', 0) if recent_anchors_row else 0
            
            # 4. Success Rates (Confirmed vs Total)
            confirmed_row = self.db.fetchone("SELECT count(*) as total FROM judgments WHERE verification_status = 'CONFIRMED'")
            confirmed_judgments = confirmed_row.get('total', 0) if confirmed_row else 0
            
            logger.info(f"[AdminStats] Anchors: {total_anchors}, Judgments: {total_judgments}, Recent: {recent_anchors}")

            return {
                "total_anchors": total_anchors,
                "total_judgments": total_judgments,
                "recent_anchors_24h": recent_anchors,
                "confirmed_judgments": confirmed_judgments,
                "server_time": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {
                "total_anchors": 0,
                "total_judgments": 0,
                "recent_anchors_24h": 0,
                "confirmed_judgments": 0,
                "error": str(e)
            }

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
                        "anchor_id": row.get('anchor_id'),
                        "email": row.get('anchor_value_masked'),
                        "created_at": row.get('created_at')
                    })
                return users
        except Exception as e:
            logger.error(f"Failed to get registered users: {e}")
            return []
