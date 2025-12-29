"""
Verification Cache Service
Simple in-memory cache for judgment verification results with TTL
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import threading

class VerificationCache:
    """Simple in-memory cache with TTL for verification results"""
    
    def __init__(self, ttl_minutes: int = 15):
        """
        Initialize cache
        
        Args:
            ttl_minutes: Time to live in minutes (default: 15)
        """
        self.ttl_minutes = ttl_minutes
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def _is_expired(self, cached_item: Dict[str, Any]) -> bool:
        """Check if cached item is expired"""
        cached_time = cached_item.get('cached_at')
        if not cached_time:
            return True
        
        expiry_time = cached_time + timedelta(minutes=self.ttl_minutes)
        return datetime.now() > expiry_time
    
    def get(self, judgment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached verification result
        
        Args:
            judgment_id: UUID of judgment
            
        Returns:
            Cached verification result or None if not found/expired
        """
        with self.lock:
            cached_item = self.cache.get(judgment_id)
            
            if not cached_item:
                return None
            
            if self._is_expired(cached_item):
                # Remove expired item
                del self.cache[judgment_id]
                return None
            
            return cached_item.get('result')
    
    def set(self, judgment_id: str, result: Dict[str, Any]) -> None:
        """
        Cache verification result
        
        Args:
            judgment_id: UUID of judgment
            result: Verification result to cache
        """
        with self.lock:
            self.cache[judgment_id] = {
                'result': result,
                'cached_at': datetime.now()
            }
    
    def invalidate(self, judgment_id: str) -> None:
        """
        Invalidate cache for specific judgment
        
        Args:
            judgment_id: UUID of judgment
        """
        with self.lock:
            if judgment_id in self.cache:
                del self.cache[judgment_id]
    
    def clear(self) -> None:
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired items
        
        Returns:
            Number of items removed
        """
        with self.lock:
            expired_keys = [
                key for key, item in self.cache.items()
                if self._is_expired(item)
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_items = len(self.cache)
            expired_items = sum(
                1 for item in self.cache.values()
                if self._is_expired(item)
            )
            
            return {
                'total_items': total_items,
                'active_items': total_items - expired_items,
                'expired_items': expired_items,
                'ttl_minutes': self.ttl_minutes
            }


# Global cache instance
verification_cache = VerificationCache(ttl_minutes=15)
