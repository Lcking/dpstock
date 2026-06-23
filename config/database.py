"""
Database Configuration
Centralized database settings
"""
import os


class DatabaseConfig:
    """Database configuration"""

    @classmethod
    def db_path(cls) -> str:
        return os.getenv("DB_PATH", "data/stocks.db")

    @classmethod
    def timeout(cls) -> float:
        return float(os.getenv("DB_TIMEOUT", "30"))

    @classmethod
    def enable_wal(cls) -> bool:
        return os.getenv("DB_ENABLE_WAL", "true").lower() == "true"

    @classmethod
    def get_connection_string(cls) -> str:
        return cls.db_path()

    @classmethod
    def validate(cls):
        db_path = cls.db_path()
        if not db_path:
            raise ValueError("DB_PATH must be set")

        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
