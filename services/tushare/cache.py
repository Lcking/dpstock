"""
Tushare Cache Layer
Memory-based caching with TTL for Tushare API responses
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from threading import Lock
from utils.logger import get_logger

logger = get_logger()


class TushareCache:
    """
    Tushare 请求缓存层
    
    Key 格式: tsr:{module}:{ts_code}:{asof}:{params_hash}
    
    TTL 配置:
    - relative_strength / industry: 900s (盘中) 
    - capital_flow: 300s
    - events: 86400s
    - stock_basic / index_weight: 604800s
    """
    
    # TTL 配置 (秒)
    TTL_CONFIG = {
        'relative_strength': 900,
        'industry_position': 900,
        'capital_flow': 300,
        'events': 86400,
        'market_structure': 900,
        'valuation': 900,
        'stock_basic': 604800,
        'index_weight': 604800,
        'default': 900
    }
    
    _instance: Optional['TushareCache'] = None
    _cache: Dict[str, Tuple[Any, datetime]] = {}
    _lock: Lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def _make_key(cls, module: str, ts_code: str, asof: str, params: Dict = None) -> str:
        """
        生成缓存键
        
        Args:
            module: 模块名称
            ts_code: 股票代码
            asof: 日期 YYYYMMDD
            params: 额外参数
        """
        params_hash = ''
        if params:
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        return f"tsr:{module}:{ts_code}:{asof}:{params_hash}"
    
    @classmethod
    def get(cls, module: str, ts_code: str, asof: str = None, params: Dict = None) -> Tuple[bool, Any]:
        """
        从缓存获取数据
        
        Returns:
            (hit, data): hit=True 表示缓存命中
        """
        if asof is None:
            asof = datetime.now().strftime('%Y%m%d')
        
        key = cls._make_key(module, ts_code, asof, params)
        
        with cls._lock:
            if key in cls._cache:
                data, expires_at = cls._cache[key]
                if datetime.now() < expires_at:
                    logger.debug(f"[TushareCache] HIT: {key}")
                    return True, data
                else:
                    # Expired, remove
                    del cls._cache[key]
                    logger.debug(f"[TushareCache] EXPIRED: {key}")
        
        logger.debug(f"[TushareCache] MISS: {key}")
        return False, None
    
    @classmethod
    def set(cls, module: str, ts_code: str, data: Any, asof: str = None, params: Dict = None, ttl: int = None):
        """
        写入缓存
        
        Args:
            module: 模块名称
            ts_code: 股票代码
            data: 要缓存的数据
            asof: 日期
            params: 额外参数
            ttl: 自定义 TTL（秒），默认使用模块配置
        """
        if asof is None:
            asof = datetime.now().strftime('%Y%m%d')
        
        if ttl is None:
            ttl = cls.TTL_CONFIG.get(module, cls.TTL_CONFIG['default'])
        
        key = cls._make_key(module, ts_code, asof, params)
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        with cls._lock:
            cls._cache[key] = (data, expires_at)
            logger.debug(f"[TushareCache] SET: {key}, TTL={ttl}s")
    
    @classmethod
    def invalidate(cls, module: str = None, ts_code: str = None):
        """
        清除缓存
        
        Args:
            module: 如果指定，只清除该模块的缓存
            ts_code: 如果指定，只清除该股票的缓存
        """
        with cls._lock:
            if module is None and ts_code is None:
                cls._cache.clear()
                logger.info("[TushareCache] All cache cleared")
                return
            
            keys_to_remove = []
            for key in cls._cache:
                parts = key.split(':')
                if len(parts) >= 3:
                    cache_module = parts[1]
                    cache_ts_code = parts[2]
                    
                    if module and module != cache_module:
                        continue
                    if ts_code and ts_code != cache_ts_code:
                        continue
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del cls._cache[key]
            
            logger.info(f"[TushareCache] Cleared {len(keys_to_remove)} entries")
    
    @classmethod
    def stats(cls) -> Dict[str, int]:
        """获取缓存统计"""
        with cls._lock:
            total = len(cls._cache)
            expired = sum(1 for _, (_, exp) in cls._cache.items() if datetime.now() >= exp)
            return {
                'total': total,
                'active': total - expired,
                'expired': expired
            }


# Singleton instance
tushare_cache = TushareCache()
