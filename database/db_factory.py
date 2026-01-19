"""
Database Factory - Centralized database connection management
Provides connection pooling and consistent database access across all services

IMPORTANT: All queries return dicts, not sqlite3.Row objects.
This eliminates the recurring .get() method issues.
"""
import sqlite3
import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def dict_factory(cursor: sqlite3.Cursor, row: Tuple) -> Dict[str, Any]:
    """
    Convert sqlite3 row to dict.
    This is the KEY fix for the recurring .get() method issues.
    """
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class DatabaseFactory:
    """
    Singleton factory for database connections.
    
    IMPORTANT: All connections use dict_factory, so:
    - cursor.fetchone() returns Dict or None
    - cursor.fetchall() returns List[Dict]
    - You can safely use row.get('field', default)
    """
    
    _instance: Optional['DatabaseFactory'] = None
    _db_path: str = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(cls, db_path: str = None):
        """Initialize database path from environment or default"""
        if db_path is None:
            db_path = os.getenv('DB_PATH', 'data/stocks.db')
        
        cls._db_path = db_path
        logger.info(f"[DatabaseFactory] Initialized with path: {db_path}")
    
    @classmethod
    def get_connection(cls) -> sqlite3.Connection:
        """
        Get a database connection with dict_factory.
        All queries will return dicts, not Row objects.
        """
        if cls._db_path is None:
            cls.initialize()
        
        conn = sqlite3.connect(cls._db_path, timeout=30.0)
        conn.row_factory = dict_factory  # KEY: Use dict_factory, not sqlite3.Row
        
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        
        return conn
    
    @classmethod
    @contextmanager
    def get_cursor(cls):
        """Context manager for database operations"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @classmethod
    def get_db_path(cls) -> str:
        """Get current database path"""
        if cls._db_path is None:
            cls.initialize()
        return cls._db_path
    
    # ==================== Safe Helper Methods ====================
    
    @classmethod
    def fetchone(cls, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Execute query and return single result as dict.
        Returns None if no result or on error.
        
        Usage:
            row = DatabaseFactory.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
            if row:
                name = row.get('name', 'Unknown')  # Safe!
        """
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
                return result  # Already dict or None
        except Exception as e:
            logger.error(f"[DatabaseFactory] fetchone error: {e}")
            return None
    
    @classmethod
    def fetchall(cls, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute query and return all results as list of dicts.
        Returns empty list if no results or on error.
        
        Usage:
            rows = DatabaseFactory.fetchall("SELECT * FROM users WHERE active = ?", (True,))
            for row in rows:
                name = row.get('name', 'Unknown')  # Safe!
        """
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                results = cursor.fetchall()
                return results if results else []
        except Exception as e:
            logger.error(f"[DatabaseFactory] fetchall error: {e}")
            return []
    
    @classmethod
    def execute(cls, query: str, params: tuple = ()) -> bool:
        """
        Execute write query (INSERT/UPDATE/DELETE).
        Returns True on success, False on error.
        
        Usage:
            success = DatabaseFactory.execute(
                "UPDATE users SET name = ? WHERE id = ?",
                (new_name, user_id)
            )
        """
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"[DatabaseFactory] execute error: {e}")
            return False
    
    @classmethod
    def execute_returning_id(cls, query: str, params: tuple = ()) -> Optional[int]:
        """
        Execute INSERT and return the lastrowid.
        Returns None on error.
        
        Usage:
            new_id = DatabaseFactory.execute_returning_id(
                "INSERT INTO users (name) VALUES (?)",
                (name,)
            )
        """
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"[DatabaseFactory] execute_returning_id error: {e}")
            return None


# ==================== Legacy Compatibility ====================

def get_db_connection() -> sqlite3.Connection:
    """
    Legacy function for backward compatibility.
    DEPRECATED: Use DatabaseFactory.get_connection() instead.
    """
    return DatabaseFactory.get_connection()
