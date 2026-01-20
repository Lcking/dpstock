"""
Anchor Service - Email Binding and Verification
Purpose: Handle email binding, verification codes, and anonymous-to-anchor migration
Constraints: Email-only binding, no user system, anonymous-first design
"""

import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Tuple
import sqlite3
from utils.logger import get_logger
from database.db_factory import DatabaseFactory

logger = get_logger()

class AnchorService:
    """Service for managing email anchors and verification"""
    
    def __init__(self, jwt_secret: str):
        self.db = DatabaseFactory()
        self.jwt_secret = jwt_secret
        
    def _get_db(self) -> sqlite3.Connection:
        """Get database connection"""
        return self.db.get_connection()
    
    # ============ Email Utilities ============
    
    @staticmethod
    def hash_email(email: str) -> str:
        """
        Hash email using SHA256
        Used for lookup without storing plaintext
        """
        return hashlib.sha256(email.lower().strip().encode()).hexdigest()
    
    @staticmethod
    def mask_email(email: str) -> str:
        """
        Mask email for display: user@example.com -> u***@example.com
        """
        try:
            local, domain = email.split('@')
            if len(local) <= 2:
                masked_local = local[0] + '***'
            else:
                masked_local = local[0] + '***' + local[-1]
            return f"{masked_local}@{domain}"
        except:
            return "***@***.com"
    
    @staticmethod
    def generate_code() -> str:
        """Generate 6-digit verification code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # ============ Verification Code Management ============
    
    def check_send_code_rate_limit(self, email_hash: str) -> Tuple[bool, str]:
        """
        Check if email can send verification code
        Returns: (allowed, error_message)
        
        Rules:
        - Max 1 send per 60 seconds
        - Max 10 sends per day
        """
        db = self._get_db()
        cursor = db.cursor()
        now = datetime.utcnow()
        
        try:
            # Check 60-second limit
            recent = cursor.execute("""
                SELECT created_at FROM email_codes 
                WHERE email_hash = ? 
                AND created_at > ?
                ORDER BY created_at DESC LIMIT 1
            """, (email_hash, (now - timedelta(seconds=60)).isoformat())).fetchone()
            
            if recent:
                return False, "请60秒后再试"
            
            # Check daily limit (10 times)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_result = cursor.execute("""
                SELECT COUNT(*) as cnt FROM email_codes
                WHERE email_hash = ?
                AND created_at > ?
            """, (email_hash, today_start.isoformat())).fetchone()
            today_count = today_result.get('cnt', 0) if today_result else 0
            
            if today_count >= 10:
                return False, "今日发送次数已达上限"
            
            return True, ""
            
        finally:
            db.close()
    
    def save_verification_code(self, email_hash: str, code: str) -> None:
        """
        Save verification code to database
        Expires in 10 minutes
        """
        db = self._get_db()
        cursor = db.cursor()
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=10)
        
        try:
            cursor.execute("""
                INSERT INTO email_codes (email_hash, code, expires_at, created_at, send_count, used)
                VALUES (?, ?, ?, ?, 1, 0)
            """, (email_hash, code, expires_at.isoformat(), now.isoformat()))
            db.commit()
            
            logger.info(f"验证码已保存 (hash: {email_hash[:8]}...)")
            
        finally:
            db.close()
    
    def verify_code(self, email_hash: str, code: str) -> Tuple[bool, str]:
        """
        Verify email code
        Returns: (valid, error_message)
        """
        db = self._get_db()
        cursor = db.cursor()
        now = datetime.utcnow()
        
        try:
            # Find valid unused code
            record = cursor.execute("""
                SELECT id, code, expires_at FROM email_codes
                WHERE email_hash = ?
                AND used = 0
                AND expires_at > ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (email_hash, now.isoformat())).fetchone()
            
            if not record:
                return False, "验证码无效或已过期"
            
            if record['code'] != code:
                return False, "验证码错误"
            
            # Mark as used
            cursor.execute("""
                UPDATE email_codes SET used = 1 WHERE id = ?
            """, (record['id'],))
            db.commit()
            
            logger.info(f"验证码验证成功 (hash: {email_hash[:8]}...)")
            return True, ""
            
        finally:
            db.close()
    
    # ============ Anchor Management ============
    
    def get_or_create_anchor(self, email: str) -> str:
        """
        Get existing anchor or create new one
        Returns: anchor_id
        """
        email_hash = self.hash_email(email)
        email_masked = self.mask_email(email)
        
        db = self._get_db()
        cursor = db.cursor()
        
        try:
            # Check if anchor exists
            existing = cursor.execute("""
                SELECT anchor_id FROM anchors
                WHERE anchor_value_hash = ?
            """, (email_hash,)).fetchone()
            
            if existing:
                logger.info(f"找到现有anchor: {existing['anchor_id']}")
                return existing['anchor_id']
            
            # Create new anchor
            import uuid
            anchor_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            cursor.execute("""
                INSERT INTO anchors (anchor_id, anchor_type, anchor_value_hash, anchor_value_masked, created_at)
                VALUES (?, 'email', ?, ?, ?)
            """, (anchor_id, email_hash, email_masked, now.isoformat()))
            db.commit()
            
            logger.info(f"创建新anchor: {anchor_id} (masked: {email_masked})")
            return anchor_id
            
        finally:
            db.close()
    
    def get_anchor_by_id(self, anchor_id: str) -> Optional[dict]:
        """Get anchor info by anchor_id"""
        db = self._get_db()
        cursor = db.cursor()
        
        try:
            anchor = cursor.execute("""
                SELECT * FROM anchors WHERE anchor_id = ?
            """, (anchor_id,)).fetchone()
            
            if anchor:
                return dict(anchor)
            return None
            
        finally:
            db.close()
    
    # ============ Token Management ============
    
    def generate_anchor_token(self, anchor_id: str) -> str:
        """
        Generate JWT token for anchor
        Expires in 30 days
        """
        payload = {
            'anchor_id': anchor_id,
            'exp': datetime.utcnow() + timedelta(days=30),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
        logger.info(f"生成token for anchor: {anchor_id}")
        return token
    
    def verify_anchor_token(self, token: str) -> Optional[str]:
        """
        Verify JWT token and return anchor_id
        Returns: anchor_id or None if invalid
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            anchor_id = payload.get('anchor_id')
            logger.debug(f"Token验证成功: {anchor_id}")
            return anchor_id
        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token无效: {str(e)}")
            return None
    
    # ============ Migration ============
    
    def migrate_anonymous_to_anchor(self, anonymous_id: str, anchor_id: str) -> int:
        """
        Migrate all judgments from anonymous to anchor
        Returns: number of migrated judgments
        
        This operation is idempotent - safe to call multiple times
        """
        db = self._get_db()
        cursor = db.cursor()
        now = datetime.utcnow()
        
        try:
            # Update judgments
            cursor.execute("""
                UPDATE judgments 
                SET owner_type = 'anchor',
                    owner_id = ?,
                    updated_at = ?
                WHERE owner_type = 'anonymous'
                AND owner_id = ?
            """, (anchor_id, now.isoformat(), anonymous_id))
            
            migrated_count = cursor.rowcount
            db.commit()
            
            logger.info(f"迁移完成: {migrated_count} 条判断从 {anonymous_id} 迁移到 {anchor_id}")
            return migrated_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"迁移失败: {str(e)}")
            raise
        finally:
            db.close()
    
    # ============ Cleanup ============
    
    def cleanup_expired_codes(self) -> int:
        """
        Clean up expired verification codes
        Returns: number of deleted codes
        """
        db = self._get_db()
        cursor = db.cursor()
        now = datetime.utcnow()
        
        try:
            cursor.execute("""
                DELETE FROM email_codes
                WHERE expires_at < ?
            """, (now.isoformat(),))
            
            deleted_count = cursor.rowcount
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"清理过期验证码: {deleted_count} 条")
            
            return deleted_count
            
        finally:
            db.close()
