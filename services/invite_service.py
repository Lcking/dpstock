"""
Invite Service
Manages invite code generation and reward distribution
"""
import sqlite3
import uuid
from datetime import date, datetime
from typing import Optional, Dict, Tuple
from utils.logger import get_logger

logger = get_logger()


class InviteService:
    """Service for managing invite codes and rewards"""
    
    REWARD_QUOTA = 5  # Quota awarded per successful invite
    
    def __init__(self, db_path: str = "data/stocks.db"):
        self.db_path = db_path
    
    def generate_invite_code(self, inviter_id: str) -> Dict:
        """
        Generate or retrieve existing invite code for a user
        
        Args:
            inviter_id: Inviter's aguai_uid
            
        Returns:
            {
                "invite_code": str,
                "is_new": bool
            }
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if user already has an invite code
                cursor.execute("""
                    SELECT invite_code FROM invite_codes
                    WHERE inviter_id = ?
                    LIMIT 1
                """, (inviter_id,))
                
                existing = cursor.fetchone()
                if existing:
                    logger.info(f"Retrieved existing invite code for user: {inviter_id}")
                    return {
                        "invite_code": existing[0],
                        "is_new": False
                    }
                
                # Generate new invite code (8-char UUID)
                invite_code = str(uuid.uuid4())[:8]
                
                cursor.execute("""
                    INSERT INTO invite_codes (invite_code, inviter_id)
                    VALUES (?, ?)
                """, (invite_code, inviter_id))
                conn.commit()
                
                logger.info(f"Generated new invite code: {invite_code} for user: {inviter_id}")
                return {
                    "invite_code": invite_code,
                    "is_new": True
                }
                
        except Exception as e:
            logger.error(f"Failed to generate invite code: {str(e)}")
            raise
    
    def validate_invite_code(self, invite_code: str) -> Optional[str]:
        """
        Validate invite code and return inviter ID
        
        Args:
            invite_code: Invite code to validate
            
        Returns:
            inviter_id if valid, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT inviter_id FROM invite_codes
                    WHERE invite_code = ?
                """, (invite_code,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Failed to validate invite code: {str(e)}")
            return None
    
    def record_invite_reward(
        self, 
        inviter_id: str, 
        invitee_id: str, 
        invite_code: str,
        reward_date: Optional[date] = None
    ) -> Tuple[bool, str]:
        """
        Record invite reward (called after invitee's first analysis)
        
        Args:
            inviter_id: Inviter's aguai_uid
            invitee_id: Invitee's aguai_uid
            invite_code: Invite code used
            reward_date: Date of reward (default: today)
            
        Returns:
            (success: bool, message: str)
        """
        if reward_date is None:
            reward_date = date.today()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if already rewarded
                cursor.execute("""
                    SELECT id FROM invite_rewards
                    WHERE inviter_id = ? AND invitee_id = ?
                """, (inviter_id, invitee_id))
                
                if cursor.fetchone():
                    logger.info(f"Invite reward already exists: inviter={inviter_id}, invitee={invitee_id}")
                    return (False, "already_rewarded")
                
                # Check daily invite limit
                cursor.execute("""
                    SELECT COALESCE(SUM(reward_quota), 0)
                    FROM invite_rewards
                    WHERE inviter_id = ? AND reward_date = ?
                """, (inviter_id, reward_date))
                
                daily_total = cursor.fetchone()[0]
                if daily_total >= 20:  # Daily limit
                    logger.info(f"Daily invite limit reached for user: {inviter_id}")
                    return (False, "daily_limit_reached")
                
                # Record reward
                cursor.execute("""
                    INSERT INTO invite_rewards 
                    (inviter_id, invitee_id, invite_code, reward_quota, reward_date)
                    VALUES (?, ?, ?, ?, ?)
                """, (inviter_id, invitee_id, invite_code, self.REWARD_QUOTA, reward_date))
                conn.commit()
                
                logger.info(f"Recorded invite reward: inviter={inviter_id}, invitee={invitee_id}, quota={self.REWARD_QUOTA}")
                return (True, "reward_granted")
                
        except sqlite3.IntegrityError as e:
            # UNIQUE constraint violation (duplicate reward)
            logger.warning(f"Duplicate invite reward attempt: {str(e)}")
            return (False, "already_rewarded")
        except Exception as e:
            logger.error(f"Failed to record invite reward: {str(e)}")
            return (False, "error")
    
    def check_and_reward_inviter(self, invitee_id: str, referrer_id: Optional[str] = None) -> Optional[Dict]:
        """
        Check if invitee should trigger a reward for their inviter
        
        Args:
            invitee_id: Invitee's aguai_uid
            referrer_id: Optional inviter ID (from cookie or parameter)
            
        Returns:
            Reward info dict if reward granted, None otherwise
        """
        if not referrer_id:
            logger.debug(f"No referrer for invitee: {invitee_id}")
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if invitee has any analysis records
                cursor.execute("""
                    SELECT COUNT(*) FROM analysis_records
                    WHERE user_id = ?
                """, (invitee_id,))
                
                analysis_count = cursor.fetchone()[0]
                
                # Only reward on first analysis
                if analysis_count != 1:
                    logger.debug(f"Invitee {invitee_id} has {analysis_count} analyses, skipping reward")
                    return None
                
                # Get invite code used
                cursor.execute("""
                    SELECT invite_code FROM invite_codes
                    WHERE inviter_id = ?
                    LIMIT 1
                """, (referrer_id,))
                
                code_result = cursor.fetchone()
                if not code_result:
                    logger.warning(f"No invite code found for inviter: {referrer_id}")
                    return None
                
                invite_code = code_result[0]
                
                # Record reward
                success, message = self.record_invite_reward(
                    inviter_id=referrer_id,
                    invitee_id=invitee_id,
                    invite_code=invite_code
                )
                
                if success:
                    return {
                        "inviter_id": referrer_id,
                        "invitee_id": invitee_id,
                        "reward_quota": self.REWARD_QUOTA,
                        "message": f"邀请成功！邀请者获得 +{self.REWARD_QUOTA} 次额度"
                    }
                else:
                    logger.info(f"Invite reward not granted: {message}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to check and reward inviter: {str(e)}")
            return None
