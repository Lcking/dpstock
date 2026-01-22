"""
Base Enhancer
Abstract base class for all enhancement modules
"""
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
from ..schemas import ModuleResult, ModuleMeta, CacheInfo
from ..client import tushare_client
from ..cache import tushare_cache
from utils.logger import get_logger

logger = get_logger()


class BaseEnhancer(ABC):
    """
    增强模块基类
    
    所有增强模块必须继承此类并实现 enhance() 方法
    """
    
    # 模块名称（必须在子类中覆盖）
    MODULE_NAME: str = "base"
    
    def __init__(self):
        self.client = tushare_client
        self.cache = tushare_cache
    
    @abstractmethod
    def enhance(self, ts_code: str, asof: str = None) -> ModuleResult:
        """
        执行增强处理
        
        Args:
            ts_code: 股票代码 (e.g., '600519.SH')
            asof: 数据日期，默认为当天
            
        Returns:
            ModuleResult: 增强结果
        """
        pass
    
    def _check_available(self) -> tuple:
        """
        检查服务是否可用
        
        Returns:
            (is_available, error_reason)
        """
        if not self.client.is_available:
            return False, "Tushare 服务不可用"
        return True, None
    
    def _get_cached(self, ts_code: str, asof: str = None) -> tuple:
        """
        从缓存获取
        
        Returns:
            (hit, data)
        """
        return self.cache.get(self.MODULE_NAME, ts_code, asof)
    
    def _set_cache(self, ts_code: str, data, asof: str = None):
        """写入缓存"""
        self.cache.set(self.MODULE_NAME, ts_code, data, asof)
    
    def _make_meta(self, asof: str, cache_hit: bool, **kwargs) -> ModuleMeta:
        """生成元数据"""
        ttl = self.cache.TTL_CONFIG.get(self.MODULE_NAME, 900)
        return ModuleMeta(
            data_source="tushare",
            asof=asof,
            cache=CacheInfo(hit=cache_hit, ttl_sec=ttl),
            **kwargs
        )
    
    def safe_enhance(self, ts_code: str, asof: str = None) -> ModuleResult:
        """
        安全执行增强（带异常捕获）
        
        这是对外暴露的主要方法，会捕获所有异常并返回降级结果
        """
        if asof is None:
            asof = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 检查服务可用性
            available, reason = self._check_available()
            if not available:
                return ModuleResult.unavailable(reason)
            
            # 执行增强
            return self.enhance(ts_code, asof)
            
        except Exception as e:
            logger.error(f"[{self.MODULE_NAME}] Enhancement failed for {ts_code}: {str(e)}")
            return ModuleResult.unavailable(f"处理异常: {str(e)}")
