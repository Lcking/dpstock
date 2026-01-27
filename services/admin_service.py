"""
Admin Service - System Statistics and User Management
Rewritten with direct sqlite3 access for maximum reliability
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sqlite3
import os
from utils.logger import get_logger

logger = get_logger()


def get_db_path() -> str:
    """Get the database path from environment or default"""
    path = os.getenv('DB_PATH', 'data/stocks.db')
    # Log the path being used for debugging
    logger.info(f"[AdminService] Using DB path: {path}, exists: {os.path.exists(path)}")
    return path


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
    """Convert sqlite3 row to dict"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class AdminService:
    """
    Service for administrative overview and statistics.
    Uses direct sqlite3 access to avoid any abstraction layer issues.
    """
    
    def __init__(self):
        self.db_path = get_db_path()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a direct database connection"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = dict_factory
        return conn
    
    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Check if a table exists in the database"""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        result = cursor.fetchone()
        return result is not None
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get global system statistics.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check table existence first
            anchors_exists = self._table_exists(conn, 'anchors')
            judgments_exists = self._table_exists(conn, 'judgments')
            
            logger.info(f"[AdminStats] Tables exist - anchors: {anchors_exists}, judgments: {judgments_exists}")
            
            # 1. Total Bound Emails (Anchors)
            total_anchors = 0
            if anchors_exists:
                cursor.execute("SELECT count(*) as cnt FROM anchors WHERE anchor_type = 'email'")
                row = cursor.fetchone()
                total_anchors = row['cnt'] if row else 0
            
            # 2. Total Judgments
            total_judgments = 0
            if judgments_exists:
                cursor.execute("SELECT count(*) as cnt FROM judgments")
                row = cursor.fetchone()
                total_judgments = row['cnt'] if row else 0
            
            # 3. Recent Bound Emails (Last 24h)
            recent_anchors = 0
            if anchors_exists:
                yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                cursor.execute(
                    "SELECT count(*) as cnt FROM anchors WHERE anchor_type = 'email' AND created_at > ?",
                    (yesterday,)
                )
                row = cursor.fetchone()
                recent_anchors = row['cnt'] if row else 0
            
            # 4. Success Rates (Confirmed vs Total)
            confirmed_judgments = 0
            if judgments_exists:
                # Check for column existence first to avoid crash if schema mismatch
                cursor.execute("PRAGMA table_info(judgments)")
                columns = [r['name'] for r in cursor.fetchall()]
                
                if 'verification_status' in columns:
                    cursor.execute("SELECT count(*) as cnt FROM judgments WHERE verification_status = 'CONFIRMED'")
                    row = cursor.fetchone()
                    confirmed_judgments = row['cnt'] if row else 0
                else:
                    logger.warning("[AdminStats] Column 'verification_status' missing from judgments table")
            
            logger.info(f"[AdminStats] Results - Anchors: {total_anchors}, Judgments: {total_judgments}, Recent: {recent_anchors}, Confirmed: {confirmed_judgments}")
            
            return {
                "total_anchors": total_anchors,
                "total_judgments": total_judgments,
                "recent_anchors_24h": recent_anchors,
                "confirmed_judgments": confirmed_judgments,
                "server_time": datetime.now().isoformat(),
                "db_path": self.db_path,
                "db_exists": os.path.exists(self.db_path)
            }
        except Exception as e:
            logger.error(f"[AdminStats] Failed to get system stats: {e}", exc_info=True)
            return {
                "total_anchors": 0,
                "total_judgments": 0,
                "recent_anchors_24h": 0,
                "confirmed_judgments": 0,
                "error": str(e),
                "db_path": self.db_path,
                "db_exists": os.path.exists(self.db_path)
            }
        finally:
            if conn:
                conn.close()

    def get_registered_users(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get list of registered users (anchors) with masked emails.
        """
        conn = None
        try:
            conn = self._get_connection()
            
            if not self._table_exists(conn, 'anchors'):
                logger.warning("[AdminService] anchors table does not exist")
                return []
            
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
            logger.error(f"[AdminService] Failed to get registered users: {e}", exc_info=True)
            return []
        finally:
            if conn:
                conn.close()
