"""
Judgment Service
Handles CRUD operations for user judgments and verification checks
"""
import sqlite3
import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from schemas.analysis_v1 import JudgmentSnapshot, JudgmentOverview, StructureStatus
from services.verification_cache import verification_cache

logger = get_logger()


class JudgmentService:
    def __init__(self, db_path: str = "data/stocks.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database and tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create judgments table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS judgments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        judgment_id TEXT UNIQUE NOT NULL,
                        user_id TEXT NOT NULL,
                        stock_code TEXT NOT NULL,
                        stock_name TEXT,
                        market_type TEXT,
                        snapshot_time TIMESTAMP NOT NULL,
                        structure_premise TEXT,
                        selected_candidates TEXT,
                        key_levels_snapshot TEXT,
                        structure_type TEXT,
                        ma200_position TEXT,
                        phase TEXT,
                        verification_period INTEGER DEFAULT 7,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Check if verification_period column exists (for migration)
                cursor.execute("PRAGMA table_info(judgments)")
                columns = [info[1] for info in cursor.fetchall()]
                if "verification_period" not in columns:
                    logger.info("Migrating database: adding verification_period column")
                    cursor.execute("ALTER TABLE judgments ADD COLUMN verification_period INTEGER DEFAULT 7")
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_judgments_user_id ON judgments(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_judgments_stock_code ON judgments(stock_code)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_judgments_created_at ON judgments(created_at DESC)")
                
                # Create judgment_checks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS judgment_checks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        judgment_id TEXT NOT NULL,
                        check_time TIMESTAMP NOT NULL,
                        current_price REAL,
                        price_change_pct REAL,
                        current_structure_status TEXT,
                        status_description TEXT,
                        reasons TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (judgment_id) REFERENCES judgments(judgment_id)
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_checks_judgment_id ON judgment_checks(judgment_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_checks_created_at ON judgment_checks(created_at DESC)")
                
                conn.commit()
                logger.debug(f"Judgment tables initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize judgment tables: {str(e)}")

    def create_judgment(self, user_id: str, snapshot: JudgmentSnapshot) -> str:
        """
        Create a new judgment snapshot
        
        Args:
            user_id: Anonymous user ID from cookie
            snapshot: JudgmentSnapshot model
            
        Returns:
            judgment_id: UUID of created judgment
        """
        try:
            judgment_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO judgments (
                        judgment_id, user_id, stock_code, stock_name, market_type,
                        snapshot_time, structure_premise, selected_candidates,
                        key_levels_snapshot, structure_type, ma200_position, phase,
                        verification_period
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    judgment_id,
                    user_id,
                    snapshot.stock_code,
                    None,  # stock_name not in JudgmentSnapshot
                    None,  # market_type not in JudgmentSnapshot
                    snapshot.snapshot_time if isinstance(snapshot.snapshot_time, str) else snapshot.snapshot_time.isoformat(),
                    json.dumps(snapshot.structure_premise),
                    json.dumps(snapshot.selected_candidates),
                    json.dumps([level.model_dump() for level in snapshot.key_levels_snapshot]),
                    snapshot.structure_type.value if hasattr(snapshot.structure_type, 'value') else snapshot.structure_type,
                    snapshot.ma200_position.value if hasattr(snapshot.ma200_position, 'value') else snapshot.ma200_position,
                    snapshot.phase.value if hasattr(snapshot.phase, 'value') else snapshot.phase,
                    getattr(snapshot, 'verification_period', 7)
                ))
                conn.commit()
                
            logger.info(f"Created judgment: {judgment_id} for user: {user_id}")
            return judgment_id
            
        except Exception as e:
            logger.error(f"Failed to create judgment: {str(e)}")
            raise

    def get_user_judgments(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all judgments for a user with latest check status
        Uses cache to avoid recalculating verification on every request
        
        Args:
            user_id: Anonymous user ID
            limit: Maximum number of results
            
        Returns:
            List of judgment overviews
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get judgments with latest check (if exists)
                cursor.execute("""
                    SELECT 
                        j.*,
                        c.current_price,
                        c.price_change_pct,
                        c.current_structure_status,
                        c.status_description,
                        c.reasons,
                        c.check_time as verification_time
                    FROM judgments j
                    LEFT JOIN (
                        SELECT judgment_id, 
                               current_price,
                               price_change_pct,
                               current_structure_status,
                               status_description,
                               reasons,
                               check_time,
                               ROW_NUMBER() OVER (PARTITION BY judgment_id ORDER BY created_at DESC) as rn
                        FROM judgment_checks
                    ) c ON j.judgment_id = c.judgment_id AND c.rn = 1
                    WHERE j.user_id = ?
                    ORDER BY j.created_at DESC
                    LIMIT ?
                """, (user_id, limit))
                
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    result = {
                        "judgment_id": row["judgment_id"],
                        "stock_code": row["stock_code"],
                        "snapshot_time": row["snapshot_time"],
                        "structure_type": row["structure_type"],
                        "ma200_position": row["ma200_position"],
                        "phase": row["phase"],
                        "verification_period": row["verification_period"],
                        "selected_candidates": json.loads(row["selected_candidates"]),
                        "created_at": row["created_at"]
                    }
                    
                    # Try to get from cache first
                    cached_check = verification_cache.get(row["judgment_id"])
                    
                    if cached_check:
                        # Use cached verification result
                        result["latest_check"] = cached_check
                        logger.debug(f"Using cached verification for judgment: {row['judgment_id']}")
                    elif row["verification_time"]:
                        # Use database check and cache it
                        check_data = {
                            "current_price": row["current_price"],
                            "price_change_pct": row["price_change_pct"],
                            "current_structure_status": row["current_structure_status"],
                            "status_description": row["status_description"],
                            "reasons": json.loads(row["reasons"]) if row["reasons"] else [],
                            "verification_time": row["verification_time"]
                        }
                        result["latest_check"] = check_data
                        
                        # Cache the result
                        verification_cache.set(row["judgment_id"], check_data)
                        logger.debug(f"Cached verification for judgment: {row['judgment_id']}")
                
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to get user judgments: {str(e)}")
            return []

    def get_judgment_detail(self, judgment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get judgment detail with latest verification result
        
        Args:
            judgment_id: UUID of judgment
            
        Returns:
            Judgment detail with latest check
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get judgment
                cursor.execute("SELECT * FROM judgments WHERE judgment_id = ?", (judgment_id,))
                judgment_row = cursor.fetchone()
                
                if not judgment_row:
                    return None
                
                # Get latest check
                cursor.execute("""
                    SELECT * FROM judgment_checks 
                    WHERE judgment_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (judgment_id,))
                check_row = cursor.fetchone()
                
                result = {
                    "judgment_id": judgment_row["judgment_id"],
                    "user_id": judgment_row["user_id"],
                    "stock_code": judgment_row["stock_code"],
                    "snapshot_time": judgment_row["snapshot_time"],
                    "structure_premise": json.loads(judgment_row["structure_premise"]),
                    "selected_candidates": json.loads(judgment_row["selected_candidates"]),
                    "key_levels_snapshot": json.loads(judgment_row["key_levels_snapshot"]),
                    "structure_type": judgment_row["structure_type"],
                    "ma200_position": judgment_row["ma200_position"],
                    "ma200_position": judgment_row["ma200_position"],
                    "phase": judgment_row["phase"],
                    "verification_period": judgment_row["verification_period"],
                    "created_at": judgment_row["created_at"]
                }
                
                if check_row:
                    result["latest_check"] = {
                        "check_time": check_row["check_time"],
                        "current_price": check_row["current_price"],
                        "price_change_pct": check_row["price_change_pct"],
                        "current_structure_status": check_row["current_structure_status"],
                        "status_description": check_row["status_description"],
                        "reasons": json.loads(check_row["reasons"]) if check_row["reasons"] else []
                    }
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get judgment detail: {str(e)}")
            return None

    def create_judgment_check(
        self, 
        judgment_id: str,
        current_price: float,
        price_change_pct: float,
        current_structure_status: str,
        status_description: str,
        reasons: List[str]
    ) -> int:
        """
        Create a verification check for a judgment
        Invalidates cache for this judgment
        
        Args:
            judgment_id: UUID of judgment
            current_price: Current stock price
            price_change_pct: Price change percentage
            current_structure_status: Structure status (maintained/weakened/broken)
            status_description: Description of status
            reasons: List of reasons for the status
            
        Returns:
            check_id: ID of created check
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO judgment_checks (
                        judgment_id, check_time, current_price, price_change_pct,
                        current_structure_status, status_description, reasons
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    judgment_id,
                    datetime.now().isoformat(),
                    current_price,
                    price_change_pct,
                    current_structure_status,
                    status_description,
                    json.dumps(reasons)
                ))
                conn.commit()
                
                check_id = cursor.lastrowid
                
                # Invalidate cache for this judgment
                verification_cache.invalidate(judgment_id)
                
                logger.info(f"Created check: {check_id} for judgment: {judgment_id}, cache invalidated")
                return check_id
                
        except Exception as e:
            logger.error(f"Failed to create judgment check: {str(e)}")
            raise
