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

    def create_judgment(self, owner_type: str, owner_id: str, snapshot: JudgmentSnapshot) -> str:
        """
        Create a new judgment snapshot
        
        Args:
            owner_type: 'anonymous' or 'anchor'
            owner_id: anonymous_id or anchor_id
            snapshot: JudgmentSnapshot model
            
        Returns:
            judgment_id: UUID of created judgment
        """
        try:
            judgment_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO judgments (
                        judgment_id, user_id, owner_type, owner_id,
                        stock_code, stock_name, market_type,
                        snapshot_time, structure_premise, selected_candidates,
                        key_levels_snapshot, structure_type, ma200_position, phase,
                        verification_period, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    judgment_id,
                    owner_id,  # Keep for backward compatibility
                    owner_type,
                    owner_id,
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
                    getattr(snapshot, 'verification_period', 7),
                    now,
                    now
                ))
                conn.commit()
                
            logger.info(f"Created judgment: {judgment_id} for {owner_type}:{owner_id}")
            return judgment_id
            
        except Exception as e:
            logger.error(f"Failed to create judgment: {str(e)}")
            raise

    def get_user_judgments(self, owner_type: str, owner_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all judgments for an owner with latest check status
        Uses cache to avoid recalculating verification on every request
        
        Args:
            owner_type: 'anonymous' or 'anchor'
            owner_id: anonymous_id or anchor_id
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
                    WHERE j.owner_type = ? AND j.owner_id = ?
                    ORDER BY j.created_at DESC
                    LIMIT ?
                """, (owner_type, owner_id, limit))
                
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    # Convert Row to dict for safe access
                    row_dict = dict(row)
                    
                    result = {
                        "judgment_id": row_dict["judgment_id"],
                        "stock_code": row_dict["stock_code"],
                        "snapshot_time": row_dict["snapshot_time"],
                        "structure_type": row_dict["structure_type"],
                        "ma200_position": row_dict["ma200_position"],
                        "phase": row_dict["phase"],
                        "verification_period": row_dict["verification_period"],
                        "selected_candidates": json.loads(row_dict["selected_candidates"]),
                        "created_at": row_dict["created_at"],
                        # Verification status fields (V1)
                        "verification_status": row_dict.get("verification_status", "WAITING"),
                        "last_checked_at": row_dict.get("last_checked_at"),
                        "verification_reason": row_dict.get("verification_reason")
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
            logger.error(f"Failed to get judgments for {owner_type}:{owner_id}: {str(e)}")
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
                
                # Convert Row to dict for easier access
                judgment_dict = dict(judgment_row)
                
                result = {
                    "judgment_id": judgment_dict["judgment_id"],
                    "user_id": judgment_dict["user_id"],
                    "owner_type": judgment_dict.get("owner_type", "anonymous"),
                    "owner_id": judgment_dict.get("owner_id", judgment_dict["user_id"]),
                    "stock_code": judgment_dict["stock_code"],
                    "snapshot_time": judgment_dict["snapshot_time"],
                    "structure_premise": json.loads(judgment_dict["structure_premise"]),
                    "selected_candidates": json.loads(judgment_dict["selected_candidates"]),
                    "key_levels_snapshot": json.loads(judgment_dict["key_levels_snapshot"]),
                    "structure_type": judgment_dict["structure_type"],
                    "ma200_position": judgment_dict["ma200_position"],
                    "phase": judgment_dict["phase"],
                    "verification_period": judgment_dict["verification_period"],
                    "created_at": judgment_dict["created_at"]
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
    
    def delete_judgment(self, judgment_id: str) -> bool:
        """
        Delete a judgment (hard delete)
        
        Args:
            judgment_id: Judgment ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "DELETE FROM judgments WHERE judgment_id = ?",
                    (judgment_id,)
                )
                conn.commit()
                
                deleted = cursor.rowcount > 0
                
                if deleted:
                    logger.info(f"Deleted judgment: {judgment_id}")
                    # Invalidate cache
                    verification_cache.invalidate(judgment_id)
                else:
                    logger.warning(f"Judgment not found for deletion: {judgment_id}")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to delete judgment {judgment_id}: {str(e)}")
            return False
    
    def check_duplicate(
        self,
        owner_type: str,
        owner_id: str,
        stock_code: str,
        structure_type: str,
        snapshot_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a duplicate judgment exists
        
        Duplicate criteria:
        - Same owner (type + id)
        - Same stock_code
        - Same structure_type
        - Same date (YYYY-MM-DD, ignoring time)
        
        Args:
            owner_type: 'anchor' or 'anonymous'
            owner_id: Owner ID
            stock_code: Stock code
            structure_type: Structure type
            snapshot_date: Snapshot date (ISO format)
            
        Returns:
            Existing judgment dict if duplicate found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Convert to string if datetime object
                if hasattr(snapshot_date, 'isoformat'):
                    snapshot_date = snapshot_date.isoformat()
                
                # Extract date part only (ignore time)
                date_part = snapshot_date.split('T')[0] if 'T' in snapshot_date else snapshot_date
                
                cursor.execute("""
                    SELECT * FROM judgments
                    WHERE owner_type = ?
                    AND owner_id = ?
                    AND stock_code = ?
                    AND structure_type = ?
                    AND DATE(snapshot_time) = DATE(?)
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (owner_type, owner_id, stock_code, structure_type, snapshot_date))
                
                row = cursor.fetchone()
                
                if row:
                    logger.warning(
                        f"Duplicate judgment found: {stock_code} {structure_type} "
                        f"on {date_part} for {owner_type}:{owner_id[:8]}..."
                    )
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to check duplicate: {str(e)}")
            return None
    
    # ==================== Verification Methods (V1) ====================
    
    def verify_judgment(self, judgment_id: str) -> Dict[str, Any]:
        """Verify a single judgment and update status"""
        from datetime import timedelta
        from services.stock_data_provider import StockDataProvider
        from services.judgment_verifier import JudgmentVerifier
        
        try:
            judgment = self.get_judgment_detail(judgment_id)
            if not judgment:
                raise ValueError(f"Judgment {judgment_id} not found")
            
            expires_at = self._compute_expires_at(
                judgment['snapshot_time'],
                judgment.get('verification_period', 1)
            )
            
            now = datetime.now()
            latest_check = self._get_latest_check(judgment_id)
            
            if now >= expires_at and not latest_check:
                self._update_verification_status(
                    judgment_id,
                    status='CHECKED',
                    reason=f"验证窗口已到期({judgment.get('verification_period', 1)}日),关键条件未触发"
                )
                return {
                    "judgment_id": judgment_id,
                    "verification_status": "CHECKED",
                    "verification_reason": f"验证窗口已到期({judgment.get('verification_period', 1)}日),关键条件未触发",
                    "last_checked_at": datetime.now().isoformat()
                }
            
            provider = StockDataProvider()
            try:
                data = provider.get_stock_data(
                    judgment['stock_code'],
                    judgment.get('market_type', 'A'),
                    days=judgment.get('verification_period', 1) + 5
                )
            except Exception as e:
                logger.error(f"Failed to get stock data: {e}")
                self._update_verification_status(judgment_id, status='CHECKED', reason="无法获取价格数据")
                return {"judgment_id": judgment_id, "verification_status": "CHECKED", "verification_reason": "无法获取价格数据", "last_checked_at": datetime.now().isoformat()}
            
            verifier = JudgmentVerifier()
            snapshot = JudgmentSnapshot(
                stock_code=judgment['stock_code'],
                snapshot_time=judgment['snapshot_time'],
                structure_premise=judgment['structure_premise'],
                selected_candidates=judgment['selected_candidates'],
                key_levels_snapshot=judgment['key_levels_snapshot'],
                structure_type=judgment['structure_type'],
                ma200_position=judgment['ma200_position'],
                phase=judgment['phase']
            )
            
            result = verifier.verify(
                snapshot=snapshot,
                current_price=data['close'][-1] if data.get('close') else 0,
                ma200_value=data.get('ma200', [None])[-1] if data.get('ma200') else None,
                price_history=data.get('close', [])[-5:] if data.get('close') else None
            )
            
            structure_status = result['current_structure_status']
            if structure_status == 'maintained':
                v_status, v_reason = 'CONFIRMED', "结构前提保持完整"
            elif structure_status == 'broken':
                v_status = 'BROKEN'
                v_reason = result['reasons'][0] if result.get('reasons') else "结构前提已被破坏"
            else:
                v_status = 'CHECKED'
                v_reason = result['reasons'][0] if result.get('reasons') else "结构前提受到挑战"
            
            self.create_judgment_check(
                judgment_id=judgment_id,
                current_price=result['current_price'],
                price_change_pct=result['price_change_pct'],
                current_structure_status=structure_status,
                status_description=v_reason,
                reasons=result.get('reasons', [])
            )
            
            self._update_verification_status(judgment_id, status=v_status, reason=v_reason)
            return {"judgment_id": judgment_id, "verification_status": v_status, "verification_reason": v_reason, "last_checked_at": datetime.now().isoformat()}
            
        except Exception as e:
            logger.error(f"Failed to verify judgment {judgment_id}: {str(e)}")
            return {"judgment_id": judgment_id, "verification_status": "WAITING", "verification_reason": f"验证失败: {str(e)}", "last_checked_at": datetime.now().isoformat()}
    
    def verify_pending_judgments(self, owner_type: str, owner_id: str, max_checks: int = 20) -> Dict[str, int]:
        """Verify pending judgments for a user (lazy trigger)"""
        try:
            judgments = self._get_judgments_needing_check(owner_type, owner_id, limit=max_checks)
            checked, updated = 0, 0
            for judgment in judgments:
                try:
                    result = self.verify_judgment(judgment['judgment_id'])
                    checked += 1
                    if result['verification_status'] != 'WAITING':
                        updated += 1
                except Exception as e:
                    logger.error(f"Failed to verify {judgment['judgment_id']}: {e}")
            logger.info(f"Lazy verification: checked={checked}, updated={updated}")
            return {"checked": checked, "updated": updated}
        except Exception as e:
            logger.error(f"Failed to verify pending judgments: {str(e)}")
            return {"checked": 0, "updated": 0}
    
    def _compute_expires_at(self, snapshot_time: str, verify_window_days: int) -> datetime:
        """Compute expiration datetime"""
        from datetime import timedelta
        try:
            if hasattr(snapshot_time, 'isoformat'):
                snapshot_dt = snapshot_time
            else:
                snapshot_dt = datetime.fromisoformat(snapshot_time.replace('Z', '+00:00'))
            return snapshot_dt + timedelta(days=verify_window_days)
        except Exception as e:
            logger.error(f"Failed to compute expires_at: {e}")
            return datetime.now() + timedelta(days=verify_window_days)
    
    def _update_verification_status(self, judgment_id: str, status: str, reason: str):
        """Update verification status in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE judgments
                    SET verification_status = ?, verification_reason = ?, last_checked_at = ?
                    WHERE judgment_id = ?
                """, (status, reason, datetime.now().isoformat(), judgment_id))
                conn.commit()
                logger.debug(f"Updated verification status for {judgment_id}: {status}")
        except Exception as e:
            logger.error(f"Failed to update verification status: {str(e)}")
    
    def _get_latest_check(self, judgment_id: str) -> Optional[Dict[str, Any]]:
        """Get latest check record for a judgment"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM judgment_checks
                    WHERE judgment_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (judgment_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get latest check: {str(e)}")
            return None
    
    def _get_judgments_needing_check(self, owner_type: str, owner_id: str, limit: int = 20) -> List[Dict]:
        """Get judgments that need verification check"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM judgments
                    WHERE owner_type = ? AND owner_id = ?
                    AND (verification_status IS NULL OR verification_status = 'WAITING')
                    AND (
                        last_checked_at IS NULL
                        OR datetime(last_checked_at) < datetime('now', '-12 hours')
                    )
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (owner_type, owner_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get judgments needing check: {str(e)}")
            return []
