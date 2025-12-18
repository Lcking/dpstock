import json
from datetime import datetime
from typing import List, AsyncGenerator, Dict, Any, Optional
from utils.logger import get_logger
from services.stock_data_provider import StockDataProvider
from services.technical_indicator import TechnicalIndicator
from services.stock_scorer import StockScorer
from services.ai_analyzer import AIAnalyzer
from services.archive_service import ArchiveService

# 获取日志器
logger = get_logger()

class StockAnalyzerService:
    """
    股票分析服务
    作为门面类协调数据提供、指标计算、评分和AI分析等组件
    """
    
    def __init__(self):
        """
        初始化股票分析服务
        使用环境变量配置的API设置
        """
        # 初始化各个组件
        self.data_provider = StockDataProvider()
        self.indicator = TechnicalIndicator()
        self.scorer = StockScorer()
        self.ai_analyzer = AIAnalyzer()
        self.archive_service = ArchiveService()
        
        logger.info("初始化StockAnalyzerService完成")
    
    async def analyze_stock(self, stock_code: str, market_type: str = 'A', stream: bool = False) -> AsyncGenerator[str, None]:
        """
        分析单只股票
        
        Args:
            stock_code: 股票代码
            market_type: 市场类型，默认为'A'股
            stream: 是否使用流式响应
            
        Returns:
            异步生成器，生成分析结果的JSON字符串
        """
        try:
            logger.info(f"开始分析股票: {stock_code}, 市场: {market_type}")
            
            # 解析股票代码和名称
            resolved_code, stock_name = self.data_provider.resolve_stock_code(stock_code)
            if resolved_code:
                stock_code = resolved_code
                logger.info(f"解析股票: 输入={stock_code}, 名称={stock_name}")

            # 获取股票数据
            df = await self.data_provider.get_stock_data(stock_code, market_type)
            
            # 检查是否有错误
            if hasattr(df, 'error'):
                error_msg = df.error
                logger.error(f"获取股票数据时出错: {error_msg}")
                yield json.dumps({
                    "stock_code": stock_code,
                    "market_type": market_type,
                    "error": error_msg,
                    "status": "error"
                })
                return
            
            # 检查数据是否为空
            if df.empty:
                error_msg = f"获取到的股票 {stock_code} 数据为空"
                logger.error(error_msg)
                yield json.dumps({
                    "stock_code": stock_code,
                    "market_type": market_type,
                    "error": error_msg,
                    "status": "error"
                })
                return
            
            # 计算技术指标
            df_with_indicators = self.indicator.calculate_indicators(df)
            
            # 计算评分
            score = self.scorer.calculate_score(df_with_indicators)
            recommendation = self.scorer.get_recommendation(score)
            
            # 获取最新数据
            latest_data = df_with_indicators.iloc[-1]
            previous_data = df_with_indicators.iloc[-2] if len(df_with_indicators) > 1 else latest_data
            
            # 价格变动绝对值
            price_change_value = latest_data['Close'] - previous_data['Close']
            
            # 优先使用原始数据中的涨跌幅(Change_pct)
            change_percent = latest_data.get('Change_pct')
            
            # 如果原始数据中没有涨跌幅，才进行计算
            if change_percent is None and previous_data['Close'] != 0:
                change_percent = (price_change_value / previous_data['Close']) * 100
            
            # 确定MA趋势
            ma_short = latest_data.get('MA5', 0)
            ma_medium = latest_data.get('MA20', 0)
            ma_long = latest_data.get('MA60', 0)
            
            if ma_short > ma_medium > ma_long:
                ma_trend = "UP"
            elif ma_short < ma_medium < ma_long:
                ma_trend = "DOWN"
            else:
                ma_trend = "FLAT"
                
            # 确定MACD信号
            macd = latest_data.get('MACD', 0)
            signal = latest_data.get('Signal', 0)
            
            if macd > signal:
                macd_signal = "BUY"
            elif macd < signal:
                macd_signal = "SELL"
            else:
                macd_signal = "HOLD"
                
            # 确定成交量状态
            volume = latest_data.get('Volume', 0)
            volume_ma = latest_data.get('Volume_MA', 0)
            
            if volume > volume_ma * 1.5:
                volume_status = "HIGH"
            elif volume < volume_ma * 0.5:
                volume_status = "LOW"
            else:
                volume_status = "NORMAL"
                
            # 当前分析日期
            analysis_date = datetime.now().strftime('%Y-%m-%d')
            
            # 生成基本分析结果
            basic_result = {
                "stock_code": stock_code,
                "name": stock_name,  # 添加股票名称
                "market_type": market_type,
                "analysis_date": analysis_date,
                "score": score,
                "price": latest_data['Close'],
                "price_change": price_change_value,  # 涨跌额 (绝对值)
                "change_percent": change_percent,  # 涨跌幅 (%)
                "ma_trend": ma_trend,
                "rsi": latest_data.get('RSI', 0),
                "macd_signal": macd_signal,
                "volume_status": volume_status,
                "recommendation": recommendation,
                "ai_analysis": ""
            }
            
            # 输出基本分析结果
            logger.info(f"基本分析结果: {json.dumps(basic_result)}")
            yield json.dumps(basic_result)
            
            # 使用AI进行深入分析
            full_analysis = ""
            async for analysis_chunk in self.ai_analyzer.get_ai_analysis(df_with_indicators, stock_code, stock_name, market_type, stream):
                if stream:
                    # 尝试从片段中提取纯文本 (如果 ai_analyzer 返回的是 JSON 字符串片段)
                    try:
                        chunk_data = json.loads(analysis_chunk)
                        if "ai_analysis_chunk" in chunk_data:
                            full_analysis += chunk_data["ai_analysis_chunk"]
                        elif "analysis" in chunk_data:
                            full_analysis = chunk_data["analysis"]
                    except:
                        pass
                else:
                    # 非流式直接就是完整 JSON
                    try:
                        chunk_data = json.loads(analysis_chunk)
                        full_analysis = chunk_data.get("analysis", "")
                    except:
                        pass
                
                yield analysis_chunk
            
            # 分析完成后，自动归档为文章
            if full_analysis:
                title = f"{datetime.now().strftime('%Y年%m月%d日')} {stock_name} {stock_code} 股票行情走势异动分析"
                article_data = {
                    "title": title,
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "market_type": market_type,
                    "content": full_analysis,
                    "score": score,
                    "publish_date": analysis_date
                }
                await self.archive_service.save_article(article_data)
                logger.info(f"文章已自动归档: {title}, 评分: {score}")
                
            logger.info(f"完成股票分析: {stock_code}")
            
        except Exception as e:
            error_msg = f"分析股票 {stock_code} 时出错: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            yield json.dumps({"error": error_msg})
    
    async def scan_stocks(self, stock_codes: List[str], market_type: str = 'A', min_score: int = 0, stream: bool = False) -> AsyncGenerator[str, None]:
        """
        批量扫描股票
        
        Args:
            stock_codes: 股票代码列表
            market_type: 市场类型
            min_score: 最低评分阈值
            stream: 是否使用流式响应
            
        Returns:
            异步生成器，生成扫描结果的JSON字符串
        """
        try:
            logger.info(f"开始批量扫描 {len(stock_codes)} 只股票, 市场: {market_type}")
            
            # 输出初始状态 - 发送批量分析初始化消息
            yield json.dumps({
                "stream_type": "batch",
                "stock_codes": stock_codes,
                "market_type": market_type,
                "min_score": min_score
            })
            
            # 解析所有股票代码
            resolved_stocks = []
            for code in stock_codes:
                r_code, r_name = self.data_provider.resolve_stock_code(code)
                if r_code:
                    resolved_stocks.append((r_code, r_name))
                else:
                    resolved_stocks.append((code, ""))
            
            # 更新代码列表为解析后的代码
            stock_codes = [s[0] for s in resolved_stocks]
            # 创建代码到名称的映射
            code_to_name = {s[0]: s[1] for s in resolved_stocks}

            # 批量获取股票数据
            stock_data_dict = await self.data_provider.get_multiple_stocks_data(stock_codes, market_type)
            
            # 计算技术指标
            stock_with_indicators = {}
            for code, df in stock_data_dict.items():
                try:
                    stock_with_indicators[code] = self.indicator.calculate_indicators(df)
                except Exception as e:
                    logger.error(f"计算 {code} 技术指标时出错: {str(e)}")
                    # 发送错误状态
                    yield json.dumps({
                        "stock_code": code,
                        "error": f"计算技术指标时出错: {str(e)}",
                        "status": "error"
                    })
            
            # 评分股票
            results = self.scorer.batch_score_stocks(stock_with_indicators)
            
            # 过滤低于最低评分的股票
            filtered_results = [r for r in results if r[1] >= min_score]
            
            # 为每只股票发送基本评分和推荐信息
            for code, score, rec in results:
                df = stock_with_indicators.get(code)
                if df is not None and len(df) > 0:
                    # 获取最新数据
                    latest_data = df.iloc[-1]
                    previous_data = df.iloc[-2] if len(df) > 1 else latest_data
                    
                    # 价格变动绝对值
                    price_change_value = latest_data['Close'] - previous_data['Close']
                    
                    # 获取涨跌幅
                    change_percent = latest_data.get('Change_pct')
                    
                    # 发送股票基本信息和评分
                    yield json.dumps({
                        "stock_code": code,
                        "name": code_to_name.get(code, ""),  # 添加股票名称
                        "score": score,
                        "recommendation": rec,
                        "price": float(latest_data.get('Close', 0)),
                        "price_change": float(price_change_value),  # 涨跌额 (绝对值)
                        "change_percent": change_percent,  # 涨跌幅 (%)
                        "rsi": float(latest_data.get('RSI', 0)) if 'RSI' in latest_data else None,
                        "ma_trend": "UP" if latest_data.get('MA5', 0) > latest_data.get('MA20', 0) else "DOWN",
                        "macd_signal": "BUY" if latest_data.get('MACD', 0) > latest_data.get('MACD_Signal', 0) else "SELL",
                        "volume_status": "HIGH" if latest_data.get('Volume_Ratio', 1) > 1.5 else ("LOW" if latest_data.get('Volume_Ratio', 1) < 0.5 else "NORMAL"),
                        "status": "completed" if score < min_score else "waiting"
                    })
            
            # 如果需要进一步分析，对评分较高的股票进行AI分析
            if stream and filtered_results:
                # 只分析前5只评分最高的股票，避免分析过多导致前端卡顿
                top_stocks = filtered_results[:5]
                
                for stock_code, score, _ in top_stocks:
                    df = stock_with_indicators.get(stock_code)
                    if df is not None:
                        # 输出正在分析的股票信息
                        yield json.dumps({
                            "stock_code": stock_code,
                            "status": "analyzing"
                        })
                        
                        # AI分析
                        async for analysis_chunk in self.ai_analyzer.get_ai_analysis(df, stock_code, code_to_name.get(stock_code, ""), market_type, stream):
                            yield analysis_chunk
            
            # 输出扫描完成信息
            yield json.dumps({
                "scan_completed": True,
                "total_scanned": len(results),
                "total_matched": len(filtered_results)
            })
            
            logger.info(f"完成批量扫描 {len(stock_codes)} 只股票, 符合条件: {len(filtered_results)}")
            
        except Exception as e:
            error_msg = f"批量扫描股票时出错: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            yield json.dumps({"error": error_msg})

    async def get_kline_data(self, stock_code: str, market_type: str = 'A', days: int = 100) -> Dict[str, Any]:
        """获取K线图数据"""
        try:
            # 这里的日期处理可以更精确，简单起见获取足够多的数据
            df = await self.data_provider.get_stock_data(stock_code, market_type)
            if df.empty or hasattr(df, 'error'):
                return {"error": "无法获取K线数据"}
            
            # 计算指标
            df = self.indicator.calculate_indicators(df)
            
            # 只取最近 N 天
            df = df.tail(days)
            
            # 格式化数据给前端 (ECharts 常用格式)
            dates = df.index.strftime('%Y-%m-%d').tolist()
            # K线数据: [开盘, 收盘, 最低, 最高]
            values = df[['Open', 'Close', 'Low', 'High']].values.tolist()
            volumes = df['Volume'].tolist()
            
            # 均线数据
            ma5 = df['MA5'].tolist() if 'MA5' in df else []
            ma20 = df['MA20'].tolist() if 'MA20' in df else []
            ma60 = df['MA60'].tolist() if 'MA60' in df else []
            
            # 副指标
            rsi = df['RSI'].tolist() if 'RSI' in df else []
            macd = df['MACD'].tolist() if 'MACD' in df else []
            macd_signal = df['Signal'].tolist() if 'Signal' in df else []
            macd_hist = df['Hist'].tolist() if 'Hist' in df else []
            
            return {
                "dates": dates,
                "values": values,
                "volumes": volumes,
                "ma5": ma5,
                "ma20": ma20,
                "ma60": ma60,
                "rsi": rsi,
                "macd": {
                    "macd": macd,
                    "signal": macd_signal,
                    "hist": macd_hist
                }
            }
        except Exception as e:
            logger.error(f"获取K线数据出错: {str(e)}")
            return {"error": str(e)}
