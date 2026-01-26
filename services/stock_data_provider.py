import pandas as pd
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from utils.logger import get_logger

# 获取日志器
logger = get_logger()

class StockDataProvider:
    """
    异步股票数据提供服务
    负责获取股票、基金等金融产品的历史数据
    """
    
    def __init__(self):
        """初始化数据提供者服务"""
        logger.debug("初始化StockDataProvider")
        self._a_share_list_cache = None
        self._hk_share_list_cache = None

    def get_a_share_list(self) -> List[Dict[str, str]]:
        """
        获取A股列表（包含代码、名称和拼音）
        带缓存机制
        """
        if self._a_share_list_cache:
            return self._a_share_list_cache
            
        try:
            import akshare as ak
            from pypinyin import pinyin, Style
            
            logger.info("正在获取A股股票列表...")
            # 获取A股代码和名称列表
            df = ak.stock_info_a_code_name()
            
            stock_list = []
            for _, row in df.iterrows():
                code = str(row['code'])
                name = str(row['name'])
                
                # 生成拼音首字母
                try:
                    py_list = pinyin(name, style=Style.FIRST_LETTER)
                    py_str = ''.join([item[0] for item in py_list]).lower()
                    # 处理多音字等异常字符，确保只保留字母数字
                    py_str = ''.join(c for c in py_str if c.isalnum())
                except Exception:
                    py_str = ""
                
                stock_list.append({
                    'code': code,
                    'name': name,
                    'pinyin': py_str
                })
                
            self._a_share_list_cache = stock_list
            logger.info(f"成功加载 {len(stock_list)} 只A股股票信息")
            return stock_list
            
        except Exception as e:
            logger.error(f"获取A股列表失败: {str(e)}")
            return []

    def get_hk_share_list(self) -> List[Dict[str, str]]:
        """
        获取港股列表（使用预定义的常用港股列表）
        避免海外服务器连接中国数据源的问题
        """
        if self._hk_share_list_cache:
            return self._hk_share_list_cache
        
        from pypinyin import pinyin, Style
        
        logger.info("使用预定义的常用港股列表")
        
        # 常用港股列表
        popular_hk_stocks = [
            ('00700', '腾讯控股'), ('00388', '香港交易所'), ('00939', '建设银行'),
            ('00941', '中国移动'), ('01299', '友邦保险'), ('02318', '中国平安'),
            ('03690', '美团'), ('00175', '吉利汽车'), ('01810', '小米集团'),
            ('00883', '中国海洋石油'), ('00005', '汇丰控股'), ('02020', '安踏体育'),
            ('01093', '石药集团'), ('00027', '银河娱乐'), ('01024', '快手'),
            ('03968', '招商银行'), ('01398', '工商银行'), ('00386', '中国石油化工'),
            ('01288', '农业银行'), ('03988', '中国银行'), ('00688', '中国海外发展'),
            ('02382', '舜宇光学科技'), ('00384', '中国燃气'), ('02269', '药明生物'),
            ('00291', '华润啤酒'), ('01109', '华润置地'), ('00016', '新鸿基地产'),
            ('00001', '长和'), ('00002', '中电控股'), ('00003', '香港中华煤气'),
            ('00006', '电能实业'), ('00011', '恒生银行'), ('00012', '恒基地产'),
            ('00013', '和记电讯'), ('00017', '新世界发展'), ('00019', '太古股份公司A'),
            ('00020', '商汤'), ('00066', '香港铁路'), ('00083', '信和置业'),
            ('00101', '恒隆地产'), ('00144', '招商局港口'), ('00151', '中国旺旺'),
            ('00168', '青岛啤酒'), ('00177', '江苏宁沪高速'), ('00267', '中信股份'),
            ('00288', '万洲国际'), ('00293', '国泰航空'), ('00316', '东方海外国际'),
            ('00322', '康师傅控股'), ('00857', '中国石油股份'), ('00968', '信义光能'),
            ('00981', '中芯国际'), ('00992', '联想集团'), ('01071', '华电国际电力股份'),
            ('01088', '中国神华'), ('01113', '长实集团'), ('01177', '中国生物制药'),
        ]
        
        stock_list = []
        for code, name in popular_hk_stocks:
            # 生成拼音首字母
            try:
                py_list = pinyin(name, style=Style.FIRST_LETTER)
                py_str = ''.join([item[0] for item in py_list]).lower()
                py_str = ''.join(c for c in py_str if c.isalnum())
            except Exception:
                py_str = ""
            
            stock_list.append({
                'code': code,
                'name': name,
                'pinyin': py_str
            })
        
        self._hk_share_list_cache = stock_list
        logger.info(f"已加载 {len(stock_list)} 只常用港股信息")
        return stock_list
    
    def resolve_stock_code(self, input_str: str, market_type: str = 'A') -> Tuple[str, str]:
        """
        解析股票输入，支持股票代码、中文名称、拼音缩写。
        智能搜索：如果主市场未找到，会尝试在全球市场中搜索。
        
        Args:
            input_str: 输入字符串
            market_type: 优先搜索的市场类型 ('A', 'HK', 'US', 'ETF', 'LOF')
            
        Returns:
            (block_code, name) 股票代码和名称的元组
        """
        input_str = input_str.strip()
        if not input_str:
            return "", ""
            
        input_lower = input_str.lower()
        
        # 市场映射和搜索顺序
        all_markets = ['A', 'HK', 'ETF', 'LOF']
        # 将主市场移到最前面
        if market_type in all_markets:
            all_markets.remove(market_type)
            all_markets.insert(0, market_type)
        elif market_type == 'US': # 美股暂时不使用本地列表匹配，直接原样返回或后续增强
            pass
        else:
            # 如果是其他奇怪的市场，默认先搜 A 股
            market_type = 'A'

        def _search_in_market(m_type):
            if m_type == 'HK':
                stock_list = self.get_hk_share_list()
            elif m_type == 'A':
                stock_list = self.get_a_share_list()
            else:
                return None

            # 1. 匹配代码
            for stock in stock_list:
                if stock['code'].lower() == input_lower:
                    return stock['code'], stock['name']
            
            # 2. 精确匹配名称或拼音
            for stock in stock_list:
                if stock['name'] == input_str or stock['pinyin'].lower() == input_lower:
                    return stock['code'], stock['name']
            
            return None

        # 尝试在所有市场中按序搜寻
        for m in all_markets:
            res = _search_in_market(m)
            if res:
                return res

        # 如果都没找到，且是美股或者看起来像美股代码 (字母)，则原样返回
        logger.warning(f"无法在缓存市场中解析股票输入: {input_str}")
        return input_str, ""

    
    async def get_stock_data(self, stock_code: str, market_type: str = 'A', 
                            start_date: Optional[str] = None, 
                            end_date: Optional[str] = None) -> pd.DataFrame:
        """
        异步获取股票或基金数据
        
        Args:
            stock_code: 股票代码
            market_type: 市场类型，默认为'A'股
            start_date: 开始日期，格式YYYYMMDD，默认为一年前
            end_date: 结束日期，格式YYYYMMDD，默认为今天
            
        Returns:
            包含历史数据的DataFrame
        """
        # 使用线程池执行同步的akshare调用
        return await asyncio.to_thread(
            self._get_stock_data_sync, 
            stock_code, 
            market_type, 
            start_date, 
            end_date
        )
    
    def _get_stock_data_sync(self, stock_code: str, market_type: str = 'A', 
                           start_date: Optional[str] = None, 
                           end_date: Optional[str] = None,
                           retries: int = 3) -> pd.DataFrame:
        """
        同步获取股票数据的实现（带重试机制）
        将被异步方法调用
        """
        # 增加递归深度限制,防止pandas比较操作时出现递归错误
        import sys
        import time
        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(10000)  # 临时增加到10000
        
        last_error = None
        for attempt in range(retries):
            try:
                result = self._fetch_stock_data_internal(stock_code, market_type, start_date, end_date)
                return result
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # 检测网络错误
                is_network_error = any(x in error_msg for x in [
                    'connection', 'timeout', 'disconnected', 'remote end closed',
                    'connectionreset', 'connectionaborted', 'networkunreachable',
                    'remotedisconnected', 'connectionerror'
                ])
                
                if is_network_error and attempt < retries - 1:
                    wait_time = (2 ** attempt) + 0.5  # 0.5s, 2.5s, 4.5s
                    logger.warning(f"[{market_type}] 网络错误获取 {stock_code}, 第 {attempt + 1}/{retries} 次重试, 等待 {wait_time}s: {str(e)[:100]}")
                    time.sleep(wait_time)
                    continue
                else:
                    # 非网络错误或最后一次尝试，直接失败
                    break
            finally:
                # 恢复原始递归限制
                sys.setrecursionlimit(old_limit)
        
        # 所有重试都失败了
        if last_error:
            logger.error(f"[{market_type}] 获取 {stock_code} 数据失败 (已重试 {retries} 次): {str(last_error)}")
            df = pd.DataFrame()
            df.error = f"获取{market_type}数据失败 {stock_code}: {str(last_error)}"
            return df
        
        return pd.DataFrame()
    
    def _fetch_stock_data_internal(self, stock_code: str, market_type: str = 'A',
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None) -> pd.DataFrame:
        """
        内部数据获取实现
        """
        # Monkey patch requests库以禁用SSL验证并添加必要的请求头
        # 这是为了解决东方财富API的SSL连接问题和反爬虫措施
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 保存原始的request方法
        original_request = requests.Session.request
        
        # 常用浏览器 User-Agent 列表
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        ]
        
        import random
        
        # 创建新的request方法,强制设置verify=False并添加headers
        def patched_request(self, method, url, **kwargs):
            kwargs['verify'] = False
            # 设置超时防止长时间挂起
            if 'timeout' not in kwargs:
                kwargs['timeout'] = (10, 30)  # (connect timeout, read timeout)
            # 添加请求头
            headers = kwargs.get('headers', {})
            if 'User-Agent' not in headers:
                headers['User-Agent'] = random.choice(user_agents)
            if 'Accept' not in headers:
                headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            if 'Accept-Language' not in headers:
                headers['Accept-Language'] = 'zh-CN,zh;q=0.9,en;q=0.8'
            if 'Connection' not in headers:
                headers['Connection'] = 'keep-alive'
            kwargs['headers'] = headers
            return original_request(self, method, url, **kwargs)
        
        # 应用monkey patch
        requests.Session.request = patched_request
        
        import akshare as ak
        
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
            
        # 确保日期格式统一（移除可能的'-'符号）
        if isinstance(start_date, str) and '-' in start_date:
            start_date = start_date.replace('-', '')
        if isinstance(end_date, str) and '-' in end_date:
            end_date = end_date.replace('-', '')
            
        try:
            if market_type == 'A':
                logger.debug(f"获取A股数据: {stock_code}")
                
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
                
            elif market_type in ['HK']:
                logger.debug(f"获取港股数据: {stock_code} (使用 yfinance)")
                try:
                    import yfinance as yf
                    
                    # 港股代码格式转换
                    # 输入: 00700 -> 输出: 0700.HK (保持4位数字)
                    # 输入: 0700.HK -> 输出: 0700.HK (保持不变)
                    if not stock_code.endswith('.HK'):
                        # 港股代码通常是5位（00700），yfinance需要4位（0700）
                        # 只去掉第一个0，保持4位数字格式
                        if len(stock_code) == 5 and stock_code.startswith('0'):
                            clean_code = stock_code[1:]  # 去掉第一个字符
                        else:
                            clean_code = stock_code  # 保持原样
                        yf_symbol = f"{clean_code}.HK"
                    else:
                        yf_symbol = stock_code
                    
                    logger.debug(f"港股代码转换: {stock_code} -> {yf_symbol}")
                    
                    ticker = yf.Ticker(yf_symbol)
                    df = ticker.history(period="1y")
                    
                    if df.empty:
                        raise ValueError(f"未获取到港股 {stock_code} 的数据，yfinance symbol: {yf_symbol}")
                    
                    logger.debug(f"港股数据列: {df.columns.tolist()}")
                    logger.debug(f"港股数据形状: {df.shape}")
                    
                except Exception as e:
                    logger.error(f"yfinance 获取港股数据失败 {stock_code}: {str(e)}")
                    raise ValueError(f"获取港股数据失败 {stock_code}: {str(e)}")
                
            elif market_type in ['US']:
                logger.debug(f"获取美股数据: {stock_code} (使用 yfinance)")
                try:
                    import yfinance as yf
                    
                    ticker = yf.Ticker(stock_code)
                    df = ticker.history(period="1y")
                    
                    if df.empty:
                        raise ValueError(f"未获取到美股 {stock_code} 的数据")
                    
                    logger.debug(f"美股数据列: {df.columns.tolist()}")
                    logger.debug(f"美股数据形状: {df.shape}")
                    
                except Exception as e:
                    logger.error(f"yfinance 获取美股数据失败 {stock_code}: {str(e)}")
                    raise ValueError(f"获取美股数据失败 {stock_code}: {str(e)}")
                    
            elif market_type in ['ETF']:
                logger.debug(f"获取{market_type}基金数据: {stock_code}")
                df = ak.fund_etf_hist_em(
                    symbol=stock_code,
                    start_date=start_date.replace('-', ''),
                    end_date=end_date.replace('-', '')
                )
            elif market_type in ['LOF']:
                logger.debug(f"获取{market_type}基金数据: {stock_code}")
                df = ak.fund_lof_hist_em(
                    symbol=stock_code,
                    start_date=start_date.replace('-', ''),
                    end_date=end_date.replace('-', '')
                )
                
            else:
                error_msg = f"不支持的市场类型: {market_type}"
                logger.error(f"[市场类型错误] {error_msg}")
                raise ValueError(error_msg)
                
            # 标准化列名
            if market_type == 'A':
                # 根据实际数据结构调整列名映射
                # 实际数据列：['日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
                df.columns = ['Date', 'Code', 'Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 'Amplitude', 'Change_pct', 'Change', 'Turnover']
            elif market_type in ['HK', 'US']:
                # yfinance 数据列：Open, High, Low, Close, Volume, Dividends, Stock Splits
                # 列名已经是首字母大写，需要添加 Amount 列
                logger.debug(f"yfinance 原始列名: {df.columns.tolist()}")
                
                # 计算成交额 Amount = Volume × Close
                if 'Volume' in df.columns and 'Close' in df.columns:
                    df['Amount'] = df['Volume'] * df['Close']
                else:
                    df['Amount'] = 0.0
                
                # 确保必需的列存在
                required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Amount']
                for col in required_cols:
                    if col not in df.columns:
                        logger.warning(f"数据中缺少{col}列，使用0值填充")
                        df[col] = 0.0
                
                # 只保留需要的列
                df = df[required_cols]
                
            elif market_type in ['ETF', 'LOF']:
                # 基金数据可能有不同的列
                df.columns = ['Date', 'Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 'Amplitude', 'Change_pct', 'Change', 'Turnover']
                
            # 确保日期列是日期类型（yfinance 默认索引就是日期）
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
            elif not isinstance(df.index, pd.DatetimeIndex):
                # 如果索引不是日期类型，尝试转换
                df.index = pd.to_datetime(df.index)
                
            # 确保按日期升序排序
            df.sort_index(inplace=True)
                
            logger.info(f"成功获取{market_type}数据 {stock_code}, 数据点数: {len(df)}")
            return df
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 检测网络错误 - 让它们向上传播以便重试
            is_network_error = any(x in error_msg for x in [
                'connection', 'timeout', 'disconnected', 'remote end closed',
                'connectionreset', 'connectionaborted', 'networkunreachable',
                'remotedisconnected', 'connectionerror'
            ])
            
            if is_network_error:
                # 重新抛出网络错误，让上层 _get_stock_data_sync 处理重试
                raise
            
            # 非网络错误：记录并返回空 DataFrame
            full_error_msg = f"获取{market_type}数据失败 {stock_code}: {str(e)}"
            logger.error(full_error_msg)
            logger.exception(e)
            df = pd.DataFrame()
            df.error = full_error_msg
            return df
            
    async def get_multiple_stocks_data(self, stock_codes: List[str], 
                                     market_type: str = 'A',
                                     start_date: Optional[str] = None, 
                                     end_date: Optional[str] = None,
                                     max_concurrency: int = 5) -> Dict[str, pd.DataFrame]:
        """
        异步批量获取多只股票数据
        
        Args:
            stock_codes: 股票代码列表
            market_type: 市场类型，默认为'A'股
            start_date: 开始日期，格式YYYYMMDD
            end_date: 结束日期，格式YYYYMMDD
            max_concurrency: 最大并发数，默认为5
            
        Returns:
            字典，键为股票代码，值为对应的DataFrame
        """
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def get_with_semaphore(code):
            async with semaphore:
                try:
                    return code, await self.get_stock_data(code, market_type, start_date, end_date)
                except Exception as e:
                    logger.error(f"获取股票 {code} 数据时出错: {str(e)}")
                    return code, None
        
        # 创建异步任务
        tasks = [get_with_semaphore(code) for code in stock_codes]
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks)
        
        # 构建结果字典，过滤掉失败的请求
        return {code: df for code, df in results if df is not None}