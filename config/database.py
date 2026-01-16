"""
Database Configuration
Centralized database settings
"""
import os


class DatabaseConfig:
    """Database configuration"""
    
    # Primary database path
    DB_PATH = os.getenv('DB_PATH', 'data/stocks.db')
    
    # Connection settings
    TIMEOUT = int(os.getenv('DB_TIMEOUT', '30'))
    
    # Enable WAL mode for better concurrency
    ENABLE_WAL = os.getenv('DB_ENABLE_WAL', 'true').lower() == 'true'
    
    @classmethod
    def get_connection_string(cls) -> str:
        """Get database connection string"""
        return cls.DB_PATH
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.DB_PATH:
            raise ValueError("DB_PATH must be set")
        
        # Ensure directory exists
        db_dir = os.path.dirname(cls.DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
