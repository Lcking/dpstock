import pandas as pd
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from services.instrument_name_resolver import infer_market_type, _normalize_code
from services.tushare.client import tushare_client
from utils.logger import get_logger

logger = get_logger()

class StockDataProvider:
    """
    异步股票数据提供服务
    负责获取股票、基金等金融产品的历史数据
    """
    _shared_a_share_list_cache: Optional[List[Dict[str, str]]] = None
    _shared_hk_share_list_cache: Optional[List[Dict[str, str]]] = None
    
    def __init__(self):
        """初始化数据提供者服务"""
        logger.debug("初始化StockDataProvider")
        self._a_share_list_cache = None
        self._hk_share_list_cache = None

    def get_a_share_list(self) -> List[Dict[str, str]]:
        """
        获取A股列表（包含代码、名称和拼音）
        带缓存机制，akshare → tushare 降级，10s 超时保护
        """
        if self._a_share_list_cache:
            return self._a_share_list_cache
        if StockDataProvider._shared_a_share_list_cache:
            self._a_share_list_cache = StockDataProvider._shared_a_share_list_cache
            return self._a_share_list_cache

        from pypinyin import pinyin, Style
        import concurrent.futures

        def _build_list(df) -> List[Dict[str, str]]:
            stock_list = []
            for _, row in df.iterrows():
                code = str(row['code'] if 'code' in row.index else row.get('ts_code', '')[:6])
                name = str(row['name'] if 'name' in row.index else row.get('name', ''))
                try:
                    py_list = pinyin(name, style=Style.FIRST_LETTER)
                    py_str = ''.join([item[0] for item in py_list]).lower()
                    py_str = ''.join(c for c in py_str if c.isalnum())
                except Exception:
                    py_str = ""
                stock_list.append({'code': code, 'name': name, 'pinyin': py_str})
            return stock_list

        # --- 尝试 akshare（带 10s 超时）---
        try:
            import akshare as ak
            logger.info("正在获取A股列表 (akshare)…")
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(ak.stock_info_a_code_name)
                df = future.result(timeout=10)
            stock_list = _build_list(df)
            self._a_share_list_cache = stock_list
            StockDataProvider._shared_a_share_list_cache = stock_list
            logger.info(f"akshare 成功加载 {len(stock_list)} 只A股")
            return stock_list
        except Exception as e:
            logger.warning(f"akshare 获取A股列表失败: {str(e)[:100]}，尝试 tushare…")

        # --- 降级：tushare ---
        try:
            import concurrent.futures
            tushare_client.ensure_initialized(log_missing_token=False)
            if tushare_client.is_available:
                logger.info("正在获取A股列表 (tushare)…")
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        tushare_client.pro.stock_basic,
                        exchange='',
                        list_status='L',
                        fields='ts_code,name',
                    )
                    ts_df = future.result(timeout=10)
                if ts_df is not None and not ts_df.empty:
                    ts_df['code'] = ts_df['ts_code'].str[:6]
                    stock_list = _build_list(ts_df)
                    self._a_share_list_cache = stock_list
                    StockDataProvider._shared_a_share_list_cache = stock_list
                    logger.info(f"tushare 成功加载 {len(stock_list)} 只A股")
                    return stock_list
        except Exception as e2:
            logger.warning(f"tushare 获取A股列表也失败: {str(e2)[:100]}")

        logger.error("所有数据源均无法获取A股列表，返回空列表")
        return []

    def get_hk_share_list(self) -> List[Dict[str, str]]:
        """
        获取港股列表（使用预定义的常用港股列表）
        避免海外服务器连接中国数据源的问题
        """
        if self._hk_share_list_cache:
            return self._hk_share_list_cache
        if StockDataProvider._shared_hk_share_list_cache:
            self._hk_share_list_cache = StockDataProvider._shared_hk_share_list_cache
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
        StockDataProvider._shared_hk_share_list_cache = stock_list
        logger.info(f"已加载 {len(stock_list)} 只常用港股信息")
        return stock_list
    
    def lookup_stock_name(self, stock_code: str, allow_network: bool = False) -> str:
        """
        尽最大努力查找股票名称：默认只查本地缓存，避免在搜索链路中做阻塞式网络调用。
        """
        # 1. 从已有缓存查
        if self._a_share_list_cache:
            for s in self._a_share_list_cache:
                if s['code'] == stock_code:
                    return s['name']

        if not allow_network:
            return ""

        # 2. 仅在显式允许时做 tushare 查询
        try:
            tushare_client.ensure_initialized(log_missing_token=False)
            if tushare_client.is_available:
                ts_code = self._to_tushare_code(stock_code)
                df = tushare_client.get_stock_basic(ts_code)
                if df is not None and not df.empty:
                    name = df.iloc[0].get('name')
                    if name:
                        return str(name)
        except Exception as e:
            logger.debug(f"tushare 查询股票名称失败: {e}")

        return ""

    def _to_tushare_code(self, stock_code: str) -> str:
        """将 6 位 A 股代码转换为 tushare ts_code。"""
        if stock_code.startswith('6'):
            return f"{stock_code}.SH"
        return f"{stock_code}.SZ"

    def _infer_eastmoney_market_id(self, stock_code: str) -> int:
        """推断东方财富 secid 市场前缀：1=上交所，0=深交所。"""
        code = _normalize_code(stock_code)
        if code.startswith(("51", "56", "58", "50")):
            return 1
        return 0

    def _to_yfinance_fund_code(self, stock_code: str) -> str:
        code = _normalize_code(stock_code)
        suffix = "SS" if code.startswith("5") else "SZ"
        return f"{code}.{suffix}"

    def _fetch_fund_hist_eastmoney(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """直接请求东方财富 K 线，避免 akshare 全量 ETF 映射在服务器上失败。"""
        import requests

        code = _normalize_code(stock_code)
        adjust_map = {"qfq": "1", "hfq": "2", "": "0"}
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params_base = {
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "klt": "101",
            "fqt": adjust_map.get(adjust, "1"),
            "beg": str(start_date).replace("-", ""),
            "end": str(end_date).replace("-", ""),
        }

        primary = self._infer_eastmoney_market_id(code)
        for market_id in (primary, 1 - primary):
            params = {**params_base, "secid": f"{market_id}.{code}"}
            try:
                resp = requests.get(url, params=params, timeout=15, verify=False)
                payload = resp.json()
            except Exception as exc:
                logger.warning(f"[Fund] eastmoney kline failed {code} secid={market_id}: {exc}")
                continue

            klines = (payload.get("data") or {}).get("klines") or []
            if not klines:
                continue

            rows = [item.split(",") for item in klines]
            df = pd.DataFrame(rows)
            if df.shape[1] < 11:
                logger.warning(f"[Fund] unexpected eastmoney columns for {code}: {df.shape[1]}")
                continue

            df = df.iloc[:, :11]
            df.columns = [
                "日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额",
                "振幅", "涨跌幅", "涨跌额", "换手率",
            ]
            for col in df.columns[1:]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            logger.info(f"[Fund] eastmoney direct OK {code} secid={market_id} rows={len(df)}")
            return df

        return pd.DataFrame()

    def _fetch_fund_hist_yfinance(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        import yfinance as yf

        code = _normalize_code(stock_code)
        yf_symbol = self._to_yfinance_fund_code(code)
        ticker = yf.Ticker(yf_symbol)
        yf_df = ticker.history(period="2y")
        if yf_df is None or yf_df.empty:
            return pd.DataFrame()

        yf_df = yf_df.reset_index()
        yf_df["Date"] = yf_df["Date"].dt.strftime("%Y%m%d")
        if start_date:
            yf_df = yf_df[yf_df["Date"] >= str(start_date).replace("-", "")]
        if end_date:
            yf_df = yf_df[yf_df["Date"] <= str(end_date).replace("-", "")]

        if yf_df.empty:
            return pd.DataFrame()

        pre_close = yf_df["Close"].shift(1)
        df = pd.DataFrame({
            "日期": yf_df["Date"],
            "开盘": yf_df["Open"],
            "收盘": yf_df["Close"],
            "最高": yf_df["High"],
            "最低": yf_df["Low"],
            "成交量": yf_df["Volume"],
            "成交额": yf_df["Volume"] * yf_df["Close"],
            "振幅": ((yf_df["High"] - yf_df["Low"]) / pre_close.replace(0, pd.NA)) * 100,
            "涨跌幅": ((yf_df["Close"] - pre_close) / pre_close.replace(0, pd.NA)) * 100,
            "涨跌额": yf_df["Close"] - pre_close,
            "换手率": 0.0,
        })
        logger.info(f"[Fund] yfinance OK {code} ({yf_symbol}) rows={len(df)}")
        return df

    @staticmethod
    def _to_sina_a_share_symbol(stock_code: str) -> str:
        """6 位 A 股代码 → 新浪 hq 符号，如 002129 → sz002129。"""
        code = _normalize_code(stock_code)
        if code.startswith(('5', '6', '9')):
            return f"sh{code}"
        return f"sz{code}"

    def fetch_a_share_sina_realtime(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        拉取 A 股新浪实时行情。

        返回字段: open, prev_close, price, high, low, volume, amount,
                  trade_date (YYYY-MM-DD), trade_time (HH:MM:SS)
        """
        import httpx

        symbol = self._to_sina_a_share_symbol(stock_code)
        url = f"https://hq.sinajs.cn/list={symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.sina.com.cn/",
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                text = resp.text
        except Exception as exc:
            logger.warning(f"[A] sina realtime failed {stock_code}: {exc}")
            return None

        # var hq_str_sz002129="名称,开盘,昨收,现价,最高,最低,买一,卖一,成交量(股),成交额,... ,日期,时间,..."
        parts = text.split('"')
        if len(parts) < 2:
            return None
        fields = parts[1].split(",")
        if len(fields) < 32:
            logger.warning(f"[A] sina realtime malformed {stock_code}: fields={len(fields)}")
            return None
        try:
            open_px = float(fields[1])
            prev_close = float(fields[2])
            price = float(fields[3])
            high = float(fields[4])
            low = float(fields[5])
            volume = float(fields[8])
            amount = float(fields[9])
            trade_date = str(fields[30]).strip()
            trade_time = str(fields[31]).strip()
        except (TypeError, ValueError) as exc:
            logger.warning(f"[A] sina realtime parse failed {stock_code}: {exc}")
            return None

        if price <= 0 or not trade_date:
            return None

        return {
            "open": open_px,
            "prev_close": prev_close,
            "price": price,
            "high": high,
            "low": low,
            "volume": volume,
            "amount": amount,
            "trade_date": trade_date,
            "trade_time": trade_time,
            "name": str(fields[0]).strip(),
        }

    def patch_a_share_latest_bar_with_realtime(
        self,
        df: pd.DataFrame,
        stock_code: str,
        quote: Optional[Dict[str, Any]] = None,
        price_tol: float = 0.005,
    ) -> pd.DataFrame:
        """
        用实时行情校正/补齐日线最后一根。

        - 日线缺当日：追加一根
        - 日线已有当日但收盘价与实时不一致：覆盖 OHLC/量额
        """
        if df is None or df.empty:
            return df
        if quote is None:
            quote = self.fetch_a_share_sina_realtime(stock_code)
        if not quote:
            return df

        try:
            trade_ts = pd.Timestamp(quote["trade_date"]).normalize()
        except Exception:
            return df

        price = float(quote["price"])
        open_px = float(quote.get("open") or price)
        high = float(quote.get("high") or price)
        low = float(quote.get("low") or price)
        prev_close = float(quote.get("prev_close") or 0)
        volume = float(quote.get("volume") or 0)
        amount = float(quote.get("amount") or 0)
        change = price - prev_close if prev_close else 0.0
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        out = df.copy()
        last_ts = pd.Timestamp(out.index[-1]).normalize()

        if trade_ts < last_ts:
            return out

        patched = False
        if trade_ts > last_ts:
            row = {col: out.iloc[-1][col] if col in out.columns else None for col in out.columns}
            row.update({
                "Open": open_px,
                "Close": price,
                "High": max(high, open_px, price),
                "Low": min(low, open_px, price) if low > 0 else min(open_px, price),
                "Volume": volume,
            })
            if "Amount" in out.columns:
                row["Amount"] = amount
            if "Change" in out.columns:
                row["Change"] = round(change, 4)
            if "Change_pct" in out.columns:
                row["Change_pct"] = round(change_pct, 4)
            if "Amplitude" in out.columns and prev_close:
                row["Amplitude"] = round((row["High"] - row["Low"]) / prev_close * 100, 4)
            out.loc[trade_ts] = row
            patched = True
            logger.info(
                f"[A] realtime append {stock_code}: {trade_ts.date()} close={price:.2f} "
                f"(hist last={last_ts.date()})"
            )
        else:
            old_close = float(out.iloc[-1]["Close"])
            old_volume = float(out.iloc[-1]["Volume"]) if "Volume" in out.columns else 0.0
            if abs(old_close - price) > price_tol or (
                volume > 0 and abs(old_volume - volume) > 1
            ):
                idx = out.index[-1]
                out.at[idx, "Close"] = price
                if "Open" in out.columns and open_px > 0:
                    out.at[idx, "Open"] = open_px
                if "High" in out.columns:
                    out.at[idx, "High"] = max(float(out.at[idx, "High"]), high, price)
                if "Low" in out.columns:
                    existing_low = float(out.at[idx, "Low"])
                    out.at[idx, "Low"] = min(
                        existing_low, low if low > 0 else existing_low, price
                    )
                if "Volume" in out.columns and volume > 0:
                    out.at[idx, "Volume"] = volume
                if "Amount" in out.columns and amount > 0:
                    out.at[idx, "Amount"] = amount
                if "Change" in out.columns:
                    out.at[idx, "Change"] = round(change, 4)
                if "Change_pct" in out.columns:
                    out.at[idx, "Change_pct"] = round(change_pct, 4)
                patched = True
                logger.info(
                    f"[A] realtime patch {stock_code}: {trade_ts.date()} "
                    f"close {old_close:.2f} -> {price:.2f}"
                )

        if patched:
            out.attrs["realtime_patched"] = True
            out.attrs["realtime_source"] = "sina"
            out.attrs["realtime_as_of"] = f"{quote['trade_date']} {quote.get('trade_time') or ''}".strip()
        return out

    def _enrich_a_share_turnover(
        self,
        df: pd.DataFrame,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        placeholder_zero: bool = False,
    ) -> pd.DataFrame:
        """
        为 A 股数据补齐换手率。

        优先保留已有真实值；若主链路缺失，则尝试用 tushare daily_basic 补齐。
        对明确来自占位的数据源（如 Yahoo 的 0.0）进行清理，避免误导性展示。
        """
        if df is None or df.empty:
            return df

        if '换手率' not in df.columns:
            df['换手率'] = pd.NA

        turnover = pd.to_numeric(df['换手率'], errors='coerce')
        has_real_turnover = turnover.notna().any() and (turnover > 0).any()

        # 修复：tushare 是惰性单例，没先 ensure_initialized() 时 is_available 会返回 False，
        # 导致 daily_basic 换手率回填路径被静默跳过、换手率始终为 NaN。
        if not has_real_turnover:
            _init = getattr(tushare_client, "ensure_initialized", None)
            if callable(_init):
                _init(log_missing_token=False)

        if not has_real_turnover and tushare_client.is_available:
            ts_code = self._to_tushare_code(stock_code)
            basic_df = None

            try:
                if hasattr(tushare_client, 'query'):
                    basic_df = tushare_client.query(
                        'daily_basic',
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date,
                        fields='ts_code,trade_date,turnover_rate',
                    )
                elif hasattr(tushare_client, 'get_daily_basic'):
                    basic_df = tushare_client.get_daily_basic(ts_code, trade_date=end_date)
            except Exception as e:
                logger.warning(f"[Turnover] tushare daily_basic 查询失败 {stock_code}: {e}")
                basic_df = None

            if basic_df is not None and not basic_df.empty and 'trade_date' in basic_df.columns:
                turnover_col = 'turnover_rate' if 'turnover_rate' in basic_df.columns else None
                if turnover_col:
                    mapped = basic_df[['trade_date', turnover_col]].copy()
                    # 关键：tushare 日期是 'YYYYMMDD'，akshare 是 'YYYY-MM-DD' 或 datetime，
                    # 必须统一成同一种 key 再 map，否则会全部对不上、悄悄全是 NaN。
                    mapped['__date_key__'] = pd.to_datetime(mapped['trade_date'], errors='coerce').dt.strftime('%Y%m%d')
                    mapped[turnover_col] = pd.to_numeric(mapped[turnover_col], errors='coerce')
                    valid = mapped.dropna(subset=['__date_key__', turnover_col])
                    turnover_map = valid.drop_duplicates('__date_key__').set_index('__date_key__')[turnover_col]

                    date_keys = pd.to_datetime(df['日期'], errors='coerce').dt.strftime('%Y%m%d')
                    aligned = date_keys.map(turnover_map)

                    before_filled = int(turnover.notna().sum())
                    turnover = turnover.where(turnover.notna(), aligned)
                    after_filled = int(turnover.notna().sum())
                    filled_count = after_filled - before_filled

                    if filled_count > 0:
                        logger.info(
                            f"[Turnover] {stock_code} 用 tushare daily_basic 回填换手率成功，"
                            f"新增 {filled_count} 行（tushare 返回 {len(turnover_map)} 行）"
                        )
                    else:
                        logger.warning(
                            f"[Turnover] {stock_code} tushare daily_basic 返回 {len(turnover_map)} 行，"
                            f"但和 akshare 日期对齐后 0 行匹配（日期格式或交易日不匹配）"
                        )
                else:
                    logger.warning(f"[Turnover] {stock_code} tushare daily_basic 缺 turnover_rate 字段")
            else:
                logger.warning(f"[Turnover] {stock_code} tushare daily_basic 返回空，换手率仍缺失")
        elif not has_real_turnover and not tushare_client.is_available:
            logger.warning(f"[Turnover] {stock_code} 上游无换手率且 tushare 不可用（TUSHARE_TOKEN 未配置或初始化失败）")

        if placeholder_zero:
            turnover = turnover.where(turnover != 0, pd.NA)

        df['换手率'] = turnover
        return df

    def resolve_stock_code(self, input_str: str, market_type: str = 'A') -> Tuple[str, str]:
        """
        解析股票输入，支持股票代码、中文名称、拼音缩写。
        智能搜索：如果主市场未找到，会尝试在全球市场中搜索。
        纯数字代码走快速路径，不依赖股票列表接口。
        """
        input_str = input_str.strip()
        if not input_str:
            return "", ""

        # 快速路径：纯数字代码（A股/ETF/LOF）直接返回，无需查列表
        if input_str.isdigit() and market_type in ('A', 'ETF', 'LOF'):
            logger.debug(f"快速路径: 纯数字代码 {input_str}，跳过列表查询")
            return input_str, ""

        # 快速路径：港股纯数字代码
        if input_str.isdigit() and market_type == 'HK':
            logger.debug(f"快速路径: 港股数字代码 {input_str}，跳过列表查询")
            return input_str, ""

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
        stock_code = _normalize_code(stock_code)
        market_type = infer_market_type(stock_code, market_type)

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
            # A股需要更长窗口以稳定计算 MA200（约 200 个交易日）
            lookback_days = 400 if market_type == 'A' else 365
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y%m%d')
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
                
                # 首先尝试 akshare
                akshare_failed = False
                try:
                    df = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq"
                    )
                    if df is not None and not df.empty:
                        df = self._enrich_a_share_turnover(
                            df,
                            stock_code=stock_code,
                            start_date=start_date,
                            end_date=end_date,
                        )
                except Exception as ak_error:
                    logger.warning(f"[A] akshare获取 {stock_code} 失败: {str(ak_error)[:80]}, 尝试tushare备用...")
                    akshare_failed = True
                
                # 如果 akshare 失败，尝试 tushare
                if akshare_failed:
                    from services.tushare.client import tushare_client
                    tushare_client.ensure_initialized(log_missing_token=False)
                    if tushare_client.is_available:
                        # 转换股票代码格式: 600519 -> 600519.SH, 000001 -> 000001.SZ
                        ts_code = self._to_tushare_code(stock_code)
                        
                        logger.info(f"[A] 使用tushare获取 {ts_code}")
                        ts_df = tushare_client.get_daily(ts_code, start_date=start_date, end_date=end_date)
                        
                        if ts_df is not None and not ts_df.empty:
                            # 转换 tushare 格式到标准格式
                            # tushare 列: ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
                            df = ts_df.rename(columns={
                                'trade_date': '日期',
                                'ts_code': '股票代码',
                                'open': '开盘',
                                'close': '收盘',
                                'high': '最高',
                                'low': '最低',
                                'vol': '成交量',  # tushare vol 单位是手(100股)
                                'amount': '成交额',  # tushare amount 单位是千元
                                'pct_chg': '涨跌幅',
                                'change': '涨跌额'
                            })
                            # 添加缺失列
                            if '振幅' not in df.columns:
                                df['振幅'] = 0.0
                            if '换手率' not in df.columns:
                                df['换手率'] = pd.NA
                            # 调整单位: vol 从手转为股
                            df['成交量'] = df['成交量'] * 100
                            # 调整单位: amount 从千元转为元
                            df['成交额'] = df['成交额'] * 1000
                            
                            # 确保列顺序和数量与后续标准化代码一致 (12列)
                            # ['Date', 'Code', 'Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 'Amplitude', 'Change_pct', 'Change', 'Turnover']
                            df = df[['日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']]
                            
                            # 调整单位: vol 从手转为股
                            df['成交量'] = df['成交量'] * 100
                            # 调整单位: amount 从千元转为元
                            df['成交额'] = df['成交额'] * 1000
                            
                            # 确保列顺序和数量与后续标准化代码一致 (12列)
                            # ['Date', 'Code', 'Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 'Amplitude', 'Change_pct', 'Change', 'Turnover']
                            df = df[['日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']]
                            
                            # 按日期排序（tushare默认是降序）
                            df = df.sort_values('日期').reset_index(drop=True)
                            df = self._enrich_a_share_turnover(
                                df,
                                stock_code=stock_code,
                                start_date=start_date,
                                end_date=end_date,
                            )
                            logger.info(f"[A] tushare成功获取 {stock_code} 数据, {len(df)} 行")
                        else:
                            logger.warning(f"[A] tushare未获取到数据 {stock_code}")
                            akshare_failed = True # 继续尝试下一级备用
                    else:
                         logger.warning(f"[A] tushare客户端不可用")
                         akshare_failed = True
                
                # 如果前两级都失败，尝试 YFinance (Yahoo Finance)
                if akshare_failed:
                    logger.info(f"[A]尝试使用Yahoo Finance获取 {stock_code}...")
                    try:
                        import yfinance as yf
                        # 转换A股代码: 600519 -> 600519.SS, 000001 -> 000001.SZ
                        if stock_code.startswith('6'):
                            yf_code = f"{stock_code}.SS"
                        else:
                            yf_code = f"{stock_code}.SZ"
                            
                        ticker = yf.Ticker(yf_code)
                        # 获取数据
                        # 需要更长窗口以覆盖 MA200（若只取 1y 可能不足）
                        yf_df = ticker.history(period="2y")
                        # 如果指定了日期，可能需要更精确的获取，这里简化为1年以覆盖大部分需求
                        
                        if not yf_df.empty:
                            # Yahoo Finance 返回索引是Date(Timestamp)，列: Open, High, Low, Close, Volume, Dividends, Stock Splits
                            # 需要重置索引把Date变成列
                            yf_df = yf_df.reset_index()
                            
                            # 格式化日期列 YYYYMMDD
                            yf_df['Date'] = yf_df['Date'].dt.strftime('%Y%m%d')
                            
                            # 筛选日期范围
                            if start_date:
                                yf_df = yf_df[yf_df['Date'] >= start_date]
                            if end_date:
                                yf_df = yf_df[yf_df['Date'] <= end_date]
                                
                            # 构造标准数据框
                            df = pd.DataFrame()
                            df['日期'] = yf_df['Date']
                            df['股票代码'] = stock_code
                            df['开盘'] = yf_df['Open']
                            df['收盘'] = yf_df['Close']
                            df['最高'] = yf_df['High']
                            df['最低'] = yf_df['Low']
                            df['成交量'] = yf_df['Volume']
                            
                            # 计算近似成交额 (Volume * Close) - Yahoo一般不提供成交额
                            df['成交额'] = df['成交量'] * df['收盘']
                            
                            # 计算涨跌幅和涨跌额 (需要前一日收盘价)
                            df['Pre_Close'] = df['收盘'].shift(1)
                            # 第一天用开盘价填充Pre_Close防止NaN
                            df.loc[df.index[0], 'Pre_Close'] = df.loc[df.index[0], '开盘']
                            
                            df['涨跌额'] = df['收盘'] - df['Pre_Close']
                            df['涨跌幅'] = (df['涨跌额'] / df['Pre_Close']) * 100
                            
                            # 振幅 = (High - Low) / Pre_Close * 100
                            df['振幅'] = ((df['最高'] - df['最低']) / df['Pre_Close']) * 100
                            
                            # 换手率 - Yahoo 不提供真实流通股本，先记占位值，后续统一清理/补齐
                            df['换手率'] = 0.0
                            
                            # 选择并排序12列
                            df = df[['日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']]
                            
                            df = self._enrich_a_share_turnover(
                                df,
                                stock_code=stock_code,
                                start_date=start_date,
                                end_date=end_date,
                                placeholder_zero=True,
                            )
                            logger.info(f"[A] Yahoo Finance成功获取 {stock_code} 数据, {len(df)} 行")
                        else:
                            raise ValueError(f"Yahoo Finance返回空数据 {yf_code}")
                            
                    except Exception as yf_e:
                        logger.error(f"[A] Yahoo Finance获取失败: {str(yf_e)}")
                        raise ValueError(f"所有数据源(Akshare, Tushare, YFinance)均无法获取 {stock_code} 数据")
                
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
                    
            elif market_type in ['ETF', 'LOF']:
                logger.debug(f"获取{market_type}基金数据: {stock_code}")
                df = self._fetch_fund_hist_eastmoney(
                    stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
                if df is None or df.empty:
                    logger.warning(f"[{market_type}] direct eastmoney empty for {stock_code}, trying akshare")
                    fetch_fn = ak.fund_etf_hist_em if market_type == 'ETF' else ak.fund_lof_hist_em
                    try:
                        df = fetch_fn(
                            symbol=stock_code,
                            period="daily",
                            start_date=start_date.replace('-', ''),
                            end_date=end_date.replace('-', ''),
                            adjust="qfq",
                        )
                    except Exception as ak_error:
                        logger.warning(f"[{market_type}] akshare failed {stock_code}: {ak_error}")
                        df = pd.DataFrame()
                if df is None or df.empty:
                    logger.info(f"[{market_type}] trying yfinance for {stock_code}")
                    df = self._fetch_fund_hist_yfinance(stock_code, start_date, end_date)
                
            else:
                error_msg = f"不支持的市场类型: {market_type}"
                logger.error(f"[市场类型错误] {error_msg}")
                raise ValueError(error_msg)
                
            # 标准化列名
            if market_type == 'A':
                # 根据实际数据结构调整列名映射
                # 实际数据列：['日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
                df.columns = ['Date', 'Code', 'Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 'Amplitude', 'Change_pct', 'Change', 'Turnover']
                if 'Turnover' in df.columns:
                    df['Turnover'] = pd.to_numeric(df['Turnover'], errors='coerce')
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
                if df is None or df.empty:
                    raise ValueError(f"未获取到{market_type}基金 {stock_code} 的数据")
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

            # A 股：日线 API 收盘后常滞后/不完整，用新浪实时价校正最后一根
            # （复现：002129 分析用了 10.72，实时收盘已是 10.66）
            if market_type == 'A' and not df.empty:
                df = self.patch_a_share_latest_bar_with_realtime(df, stock_code)

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