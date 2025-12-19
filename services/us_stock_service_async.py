import asyncio
import pandas as pd
from typing import List, Dict, Any, Optional
from utils.logger import get_logger

# 获取日志器
logger = get_logger()

class USStockServiceAsync:
    """
    美股服务
    提供美股数据的搜索和获取功能
    """
    
    def __init__(self):
        """初始化美股服务"""
        logger.debug("初始化USStockServiceAsync")
        
        # 可选：添加缓存以减少频繁请求
        self._cache = None
        self._cache_timestamp = None
    
    async def search_us_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """
        异步搜索美股代码
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的股票列表
        """
        max_retries = 3
        retry_delay = 1  # 秒
        
        for attempt in range(max_retries):
            try:
                logger.info(f"异步搜索美股: {keyword} (尝试 {attempt + 1}/{max_retries})")
                
                # 使用线程池执行同步的akshare调用
                df = await asyncio.to_thread(self._get_us_stocks_data)
                
                # 模糊匹配搜索 (代码, 名称, 拼音)
                keyword_lower = keyword.lower()
                mask = (df['name'].str.contains(keyword, case=False, na=False) | 
                       df['symbol'].str.contains(keyword, case=False, na=False) |
                       df['pinyin'].str.contains(keyword_lower, case=False, na=False))
                results = df[mask]
                
                # 格式化返回结果并处理 NaN 值
                formatted_results = []
                for _, row in results.iterrows():
                    formatted_results.append({
                        'name': row['name'] if pd.notna(row['name']) else '',
                        'symbol': str(row['symbol']) if pd.notna(row['symbol']) else '',
                        'price': float(row['price']) if pd.notna(row['price']) else 0.0,
                        'market_value': float(row['market_value']) if pd.notna(row['market_value']) else 0.0
                    })
                    # 限制只返回前10个结果
                    if len(formatted_results) >= 10:
                        break
                
                logger.info(f"美股搜索完成，找到 {len(formatted_results)} 个匹配项（限制显示前10个）")
                return formatted_results
                
            except Exception as e:
                error_msg = f"搜索美股代码失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
                logger.warning(error_msg)
                
                # 如果是连接错误，等待后重试
                if attempt < max_retries - 1:
                    if "Connection" in str(e) or "reset" in str(e).lower():
                        logger.info(f"连接错误，{retry_delay}秒后重试...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                
                # 最后一次尝试失败，记录错误但返回空列表而不是抛异常
                logger.error(f"搜索美股代码最终失败: {str(e)}")
                # 返回空列表，让前端可以正常工作
                return []
        
        return []
    
    def _get_us_stocks_data(self) -> pd.DataFrame:
        """
        获取美股数据（同步方法，将被异步方法调用）
        
        Returns:
            包含美股数据的DataFrame
        """
        import akshare as ak
        from pypinyin import pinyin, Style
        
        try:
            # 获取美股数据
            df = ak.stock_us_spot_em()
            
            # 转换列名
            df = df.rename(columns={
                "序号": "index",
                "名称": "name",
                "最新价": "price",
                "涨跌额": "price_change",
                "涨跌幅": "price_change_percent",
                "开盘价": "open",
                "最高价": "high",
                "最低价": "low",
                "昨收价": "pre_close",
                "总市值": "market_value",
                "市盈率": "pe_ratio",
                "成交量": "volume",
                "成交额": "turnover",
                "振幅": "amplitude",
                "换手率": "turnover_rate",
                "代码": "symbol"
            })
            
            # 生成拼音首字母
            def get_pinyin(name):
                if not name or not isinstance(name, str):
                    return ""
                try:
                    py_list = pinyin(name, style=Style.FIRST_LETTER)
                    return ''.join([item[0] for item in py_list]).lower()
                except:
                    return ""
            
            df['pinyin'] = df['name'].apply(get_pinyin)
            
            return df
            
        except Exception as e:
            logger.error(f"获取美股数据失败: {str(e)}")
            logger.exception(e)
            raise Exception(f"获取美股数据失败: {str(e)}")
            
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
            
            # 使用线程池执行同步的akshare调用
            df = await asyncio.to_thread(self._get_us_stocks_data)
            
            # 精确匹配股票代码
            result = df[df['symbol'] == symbol]
            
            if len(result) == 0:
                raise Exception(f"未找到股票代码: {symbol}")
            
            # 获取第一行数据
            row = result.iloc[0]
            
            # 格式化为字典
            stock_detail = {
                'name': row['name'] if pd.notna(row['name']) else '',
                'symbol': str(row['symbol']) if pd.notna(row['symbol']) else '',
                'price': float(row['price']) if pd.notna(row['price']) else 0.0,
                'price_change': float(row['price_change']) if pd.notna(row['price_change']) else 0.0,
                'price_change_percent': float(row['price_change_percent'].strip('%'))/100 if pd.notna(row['price_change_percent']) else 0.0,
                'open': float(row['open']) if pd.notna(row['open']) else 0.0,
                'high': float(row['high']) if pd.notna(row['high']) else 0.0,
                'low': float(row['low']) if pd.notna(row['low']) else 0.0,
                'pre_close': float(row['pre_close']) if pd.notna(row['pre_close']) else 0.0,
                'market_value': float(row['market_value']) if pd.notna(row['market_value']) else 0.0,
                'pe_ratio': float(row['pe_ratio']) if pd.notna(row['pe_ratio']) else 0.0,
                'volume': float(row['volume']) if pd.notna(row['volume']) else 0.0,
                'turnover': float(row['turnover']) if pd.notna(row['turnover']) else 0.0
            }
            
            logger.info(f"获取美股详情成功: {symbol}")
            return stock_detail
            
        except Exception as e:
            error_msg = f"获取美股详情失败: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            raise Exception(error_msg) 