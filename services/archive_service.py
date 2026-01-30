"""
Archive Service
Manages article storage and retrieval

REFACTORED: Uses DatabaseFactory for unified database access
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from database.db_factory import DatabaseFactory

logger = get_logger()

class ArchiveService:
    def __init__(self, db_path: str = "data/stocks.db"):
        self.db_path = db_path
        self.db = DatabaseFactory
        DatabaseFactory.initialize(db_path)
        self._init_db()

    def _init_db(self):
        """初始化数据库和表结构"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        stock_code TEXT NOT NULL,
                        stock_name TEXT NOT NULL,
                        market_type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        score INTEGER,
                        legacy_score INTEGER,
                        score_version TEXT,
                        ai_score_json TEXT,
                        publish_date TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(title)
                    )
                """)
                # Backward-compatible migration for existing DBs
                self._ensure_article_columns(conn)
                conn.commit()
                logger.debug(f"数据库初始化成功: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")

    def _ensure_article_columns(self, conn: sqlite3.Connection):
        """
        Ensure new columns exist for backward compatibility.
        SQLite supports ADD COLUMN but not DROP COLUMN.
        """
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(articles)")
            existing = {row["name"] for row in cursor.fetchall() if row and row.get("name")}

            columns: Dict[str, str] = {
                "legacy_score": "INTEGER",
                "score_version": "TEXT",
                "ai_score_json": "TEXT",
            }

            for col, col_type in columns.items():
                if col not in existing:
                    logger.info(f"[Archive] Migrating articles: ADD COLUMN {col} {col_type}")
                    cursor.execute(f"ALTER TABLE articles ADD COLUMN {col} {col_type}")
        except Exception as e:
            logger.warning(f"[Archive] Failed to ensure article columns: {e}")

    async def save_article(self, article_data: Dict[str, Any]) -> int:
        """保存或更新文章 (De-duplication by title)"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # 使用 REPLACE INTO 实现去重覆盖
                cursor.execute("""
                    REPLACE INTO articles 
                    (title, stock_code, stock_name, market_type, content, score, legacy_score, score_version, ai_score_json, publish_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_data['title'],
                    article_data['stock_code'],
                    article_data['stock_name'],
                    article_data['market_type'],
                    article_data['content'],
                    article_data.get('score'),
                    article_data.get('legacy_score'),
                    article_data.get('score_version'),
                    article_data.get('ai_score_json'),
                    article_data.get('publish_date', datetime.now().strftime("%Y-%m-%d"))
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"保存文章时出错: {str(e)}, 数据: {article_data}")
            return -1

    async def get_articles(self, limit: int = 20, offset: int = 0, keyword: str = None) -> List[Dict[str, Any]]:
        """获取文章列表，支持关键字搜索"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                if keyword:
                    sql = """
                        SELECT * FROM articles 
                        WHERE title LIKE ? OR stock_code LIKE ? OR stock_name LIKE ?
                        ORDER BY publish_date DESC, created_at DESC 
                        LIMIT ? OFFSET ?
                    """
                    pattern = f"%{keyword}%"
                    params = (pattern, pattern, pattern, limit, offset)
                else:
                    sql = """
                        SELECT * FROM articles 
                        ORDER BY publish_date DESC, created_at DESC 
                        LIMIT ? OFFSET ?
                    """
                    params = (limit, offset)
                    
                cursor.execute(sql, params)
                return cursor.fetchall()  # Already list of dicts due to dict_factory
        except Exception as e:
            logger.error(f"获取文章列表出错: {str(e)}")
            return []

    async def get_article_by_id(self, article_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取文章详情"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
                return cursor.fetchone()  # Already dict or None
        except Exception as e:
            logger.error(f"获取文章详情出错: {str(e)}")
            return None
