import asyncio
import pandas as pd
from typing import List, Dict, Any, Optional
from utils.logger import get_logger

# 获取日志器
logger = get_logger()

class USStockServiceAsync:
    """
    美股服务 - 使用 yfinance 数据源
    提供美股数据的搜索和获取功能
    """
    
    def __init__(self):
        """初始化美股服务"""
        logger.debug("初始化USStockServiceAsync (使用 yfinance)")
        
        # 常用美股列表缓存
        self._popular_stocks_cache = None
        
    async def search_us_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        异步搜索美股代码
        使用 yfinance Ticker.info 进行搜索
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的股票列表
        """
        try:
            logger.info(f"异步搜索美股: {keyword}")
            
            # 常用美股列表（可以根据需要扩展）
            popular_symbols = await self._get_popular_us_stocks()
            
            # 关键词匹配
            keyword_lower = keyword.lower()
            results = []
            
            for stock in popular_symbols:
                symbol = stock['symbol'].lower()
                name = stock['name'].lower()
                
                if keyword_lower in symbol or keyword_lower in name:
                    results.append(stock)
                    if len(results) >= 10:
                        break
            
            logger.info(f"美股搜索完成，找到 {len(results)} 个匹配项")
            return results
            
        except Exception as e:
            logger.error(f"搜索美股代码失败: {str(e)}")
            return []
    
    async def _get_popular_us_stocks(self) -> List[Dict[str, Any]]:
        """
        获取常用美股列表
        """
        if self._popular_stocks_cache:
            return self._popular_stocks_cache
        
        # 常用美股代码（可扩展）
        popular_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
            'JPM', 'V', 'JNJ', 'WMT', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV',
            'KO', 'PEP', 'COST', 'AVGO', 'MCD', 'CSCO', 'ACN', 'TMO', 'DHR',
            'VZ', 'ADBE', 'NFLX', 'CRM', 'NKE', 'DIS', 'ABT', 'TXN', 'PM',
            'UNH', 'BAC', 'ORCL', 'INTC', 'AMD', 'QCOM', 'CMCSA', 'UPS',
            'IBM', 'AMGN', 'BA', 'GE', 'CAT', 'GS'
        ]
        
        # 获取详细信息
        stocks = []
        for symbol in popular_symbols:
            try:
                info = await asyncio.to_thread(self._get_stock_info, symbol)
                if info:
                    stocks.append({
                        'symbol': symbol,
                        'name': info.get('longName', info.get('shortName', symbol)),
                        'price': info.get('currentPrice', info.get('regularMarketPrice', 0.0)),
                        'market_value': info.get('marketCap', 0.0)
                    })
            except Exception as e:
                logger.warning(f"获取 {symbol} 信息失败: {e}")
                # 添加基本信息
                stocks.append({
                    'symbol': symbol,
                    'name': symbol,
                    'price': 0.0,
                    'market_value': 0.0
                })
        
        self._popular_stocks_cache = stocks
        logger.info(f"已加载 {len(stocks)} 只常用美股信息")
        return stocks
    
    def _get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取单个股票信息（同步方法）
        """
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            return ticker.info
        except Exception as e:
            logger.warning(f"yfinance 获取 {symbol} 信息失败: {e}")
            return None
    
    async def get_us_stock_detail(self, symbol: str) -> Dict[str, Any]:
        """
        异步获取单个美股详细信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            股票详细信息
        """
        try:
            logger.info(f"获取美股详情: {symbol}")
            
            info = await asyncio.to_thread(self._get_stock_info, symbol)
            
            if not info:
                raise Exception(f"未找到股票: {symbol}")
            
            # 格式化为统一结构
            stock_detail = {
                'name': info.get('longName', info.get('shortName', symbol)),
                'symbol': symbol,
                'price': float(info.get('currentPrice', info.get('regularMarketPrice', 0.0))),
                'price_change': float(info.get('regularMarketChange', 0.0)),
                'price_change_percent': float(info.get('regularMarketChangePercent', 0.0)) / 100,
                'open': float(info.get('regularMarketOpen', info.get('open', 0.0))),
                'high': float(info.get('dayHigh', info.get('regularMarketDayHigh', 0.0))),
                'low': float(info.get('dayLow', info.get('regularMarketDayLow', 0.0))),
                'pre_close': float(info.get('previousClose', info.get('regularMarketPreviousClose', 0.0))),
                'market_value': float(info.get('marketCap', 0.0)),
                'pe_ratio': float(info.get('trailingPE', info.get('forwardPE', 0.0))),
                'volume': float(info.get('volume', info.get('regularMarketVolume', 0.0))),
                'turnover': float(info.get('volume', 0.0)) * float(info.get('currentPrice', 0.0))
            }
            
            logger.info(f"获取美股详情成功: {symbol}")
            return stock_detail
            
        except Exception as e:
            error_msg = f"获取美股详情失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)