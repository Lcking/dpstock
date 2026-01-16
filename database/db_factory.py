"""
Database Factory - Centralized database connection management
Provides connection pooling and consistent database access across all services
"""
import sqlite3
import os
from typing import Optional
from contextlib import contextmanager


class DatabaseFactory:
    """Singleton factory for database connections"""
    
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
        print(f"[DatabaseFactory] Initialized with path: {db_path}")
    
    @classmethod
    def get_connection(cls) -> sqlite3.Connection:
        """Get a database connection"""
        if cls._db_path is None:
            cls.initialize()
        
        conn = sqlite3.connect(cls._db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        
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
