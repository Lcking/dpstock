"""
Watchlist Summary Cache
Simple in-memory cache for watchlist item summaries with TTL
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import threading
from utils.logger import get_logger

logger = get_logger()


class WatchlistSummaryCache:
    """
    In-memory cache for WatchlistItemSummary objects.
    
    Key format: {ts_code}:{asof_date}
    Example: 600519.SH:2026-01-26
    """
    
    def __init__(self, ttl_minutes: int = 5):
        """
        Initialize cache
        
        Args:
            ttl_minutes: Time to live in minutes (default: 5)
        """
        self.ttl_minutes = ttl_minutes
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def _make_key(self, ts_code: str, asof: str) -> str:
        """Generate cache key"""
        return f"{ts_code}:{asof}"
    
    def _is_expired(self, cached_item: Dict[str, Any]) -> bool:
        """Check if cached item is expired"""
        cached_time = cached_item.get('cached_at')
        if not cached_time:
            return True
        
        expiry_time = cached_time + timedelta(minutes=self.ttl_minutes)
        return datetime.now() > expiry_time
    
    def get(self, ts_code: str, asof: str) -> Optional[Any]:
        """
        Get cached summary
        
        Args:
            ts_code: Stock code (e.g., 600519.SH)
            asof: Date string (e.g., 2026-01-26)
            
        Returns:
            Cached WatchlistItemSummary or None if not found/expired
        """
        key = self._make_key(ts_code, asof)
        
        with self._lock:
            cached_item = self.cache.get(key)
            
            if not cached_item:
                return None
            
            if self._is_expired(cached_item):
                del self.cache[key]
                return None
            
            logger.debug(f"[WatchlistCache] HIT {ts_code}")
            return cached_item.get('data')
    
    def set(self, ts_code: str, asof: str, data: Any) -> None:
        """
        Cache a summary
        
        Args:
            ts_code: Stock code
            asof: Date string
            data: WatchlistItemSummary object to cache
        """
        key = self._make_key(ts_code, asof)
        
        with self._lock:
            self.cache[key] = {
                'data': data,
                'cached_at': datetime.now()
            }
            logger.debug(f"[WatchlistCache] SET {ts_code}")
    
    def invalidate(self, ts_code: str, asof: str) -> None:
        """Invalidate cache for specific stock+date"""
        key = self._make_key(ts_code, asof)
        
        with self._lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self) -> None:
        """Clear all cache"""
        with self._lock:
            self.cache.clear()
            logger.info("[WatchlistCache] Cleared all cache")
    
    def cleanup_expired(self) -> int:
        """Remove all expired items, returns count removed"""
        with self._lock:
            expired_keys = [
                key for key, item in self.cache.items()
                if self._is_expired(item)
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.debug(f"[WatchlistCache] Cleaned up {len(expired_keys)} expired items")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
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


# Global cache instance with 5-minute TTL
watchlist_summary_cache = WatchlistSummaryCache(ttl_minutes=5)
