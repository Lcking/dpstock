"""
Tushare Pro API Client
Secure token handling via environment variables only
"""
import os
import tushare as ts
from typing import Optional, Dict, Any
from datetime import datetime
from utils.logger import get_logger

logger = get_logger()


class TushareClient:
    """
    Tushare Pro API 客户端封装
    
    安全说明:
    - Token 仅从环境变量 TUSHARE_TOKEN 读取
    - 绝不在日志中输出完整 Token
    """
    
    _instance: Optional['TushareClient'] = None
    _pro: Optional[ts.pro_api] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not TushareClient._initialized:
            self._setup()
            TushareClient._initialized = True
    
    def _setup(self):
        """Initialize Tushare Pro API"""
        token = os.getenv('TUSHARE_TOKEN', '')
        
        if not token:
            logger.warning("[Tushare] TUSHARE_TOKEN not set, data enhancement will be unavailable")
            return
        
        try:
            ts.set_token(token)
            TushareClient._pro = ts.pro_api()
            # Test connection with a simple query
            logger.info("[Tushare] Client initialized successfully (token: ***hidden***)")
        except Exception as e:
            logger.error(f"[Tushare] Failed to initialize: {str(e)}")
            TushareClient._pro = None
    
    @property
    def pro(self) -> Optional[ts.pro_api]:
        """Get Tushare Pro API instance"""
        return TushareClient._pro
    
    @property
    def is_available(self) -> bool:
        """Check if Tushare is available"""
        return TushareClient._pro is not None
    
    def query(self, api_name: str, retries: int = 3, **kwargs) -> Optional[Any]:
        """
        Execute Tushare API query with error handling and retry
        
        Args:
            api_name: Tushare API name (e.g., 'daily', 'index_daily')
            retries: Number of retry attempts for network errors
            **kwargs: API parameters
            
        Returns:
            DataFrame or None on error
        """
        if not self.is_available:
            logger.warning(f"[Tushare] Query '{api_name}' skipped - client not available")
            return None
        
        import time
        
        for attempt in range(retries):
            try:
                result = getattr(self.pro, api_name)(**kwargs)
                logger.debug(f"[Tushare] Query '{api_name}' returned {len(result) if result is not None else 0} rows")
                return result
            except Exception as e:
                error_msg = str(e)
                
                # Don't retry on permission errors
                if 'permission' in error_msg.lower() or '权限' in error_msg:
                    logger.warning(f"[Tushare] Permission denied for '{api_name}': {error_msg}")
                    return None
                
                # Network errors - retry with exponential backoff
                is_network_error = any(x in error_msg.lower() for x in [
                    'connection', 'timeout', 'disconnected', 'remote end closed',
                    'connectionreset', 'connectionaborted', 'networkunreachable'
                ])
                
                if is_network_error and attempt < retries - 1:
                    wait_time = (2 ** attempt) + 0.5  # 0.5s, 2.5s, 4.5s
                    logger.warning(f"[Tushare] Network error on '{api_name}', retry {attempt + 1}/{retries} in {wait_time}s: {error_msg}")
                    time.sleep(wait_time)
                    continue
                
                # Final failure
                logger.error(f"[Tushare] Query '{api_name}' failed after {attempt + 1} attempts: {error_msg}")
                return None
        
        return None
    
    def get_daily(self, ts_code: str, start_date: str = None, end_date: str = None, days: int = 60):
        """
        获取日线行情
        
        Args:
            ts_code: 股票代码 (e.g., '600519.SH')
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            days: 如果未指定日期范围，获取最近N天
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        return self.query('daily', ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    def get_index_daily(self, ts_code: str, start_date: str = None, end_date: str = None):
        """
        获取指数日线行情
        
        Args:
            ts_code: 指数代码 (e.g., '000300.SH' for 沪深300)
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        return self.query('index_daily', ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    def get_moneyflow(self, ts_code: str, start_date: str = None, end_date: str = None):
        """
        获取个股资金流向
        
        注意: 此接口可能需要较高积分权限
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        return self.query('moneyflow', ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    def get_stock_basic(self, ts_code: str = None):
        """
        获取股票基础信息（含行业分类）
        """
        if ts_code:
            return self.query('stock_basic', ts_code=ts_code, fields='ts_code,name,industry,market,list_date')
        return self.query('stock_basic', fields='ts_code,name,industry,market,list_date')
    
    def get_daily_basic(self, ts_code: str, trade_date: str = None):
        """
        获取每日指标（PE/PB/换手率等）
        """
        if not trade_date:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        return self.query('daily_basic', ts_code=ts_code, trade_date=trade_date)


# Singleton instance
tushare_client = TushareClient()
