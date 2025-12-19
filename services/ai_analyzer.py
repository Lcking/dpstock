import pandas as pd
import os
import json
import httpx
import re
from typing import AsyncGenerator
from dotenv import load_dotenv
from utils.logger import get_logger
from utils.api_utils import APIUtils
from datetime import datetime
from services.stock_scorer import StockScorer

# 获取日志器
logger = get_logger()

class AIAnalyzer:
    """
    异步AI分析服务
    负责调用AI API对股票数据进行分析
    """
    
    def __init__(self):
        """
        初始化AI分析服务
        使用环境变量配置
        """
        # 加载环境变量
        load_dotenv()
        
        # 设置API配置（使用环境变量）
        self.API_URL = os.getenv('API_URL')
        self.API_KEY = os.getenv('API_KEY')
        self.API_MODEL = os.getenv('API_MODEL', 'deepseek-reasoner')
        self.API_TIMEOUT = int(os.getenv('API_TIMEOUT', 60))
        
        # 初始化统一评分器
        self.scorer = StockScorer()
        
        logger.debug(f"初始化AIAnalyzer: API_URL={self.API_URL}, API_MODEL={self.API_MODEL}, API_KEY={'已提供' if self.API_KEY else '未提供'}, API_TIMEOUT={self.API_TIMEOUT}")
    
    async def get_ai_analysis(self, df: pd.DataFrame, stock_code: str, stock_name: str = "", market_type: str = 'A', stream: bool = False) -> AsyncGenerator[str, None]:
        """
        对股票数据进行AI分析
        
        Args:
            df: 包含技术指标的DataFrame
            stock_code: 股票代码
            stock_name: 股票名称
            market_type: 市场类型，默认为'A'股
            stream: 是否使用流式响应
            
        Returns:
            异步生成器，生成分析结果字符串
        """
        try:
            name_display = f"{stock_name} ({stock_code})" if stock_name else stock_code
            logger.info(f"开始AI分析 {name_display}, 流式模式: {stream}")
            
            # 提取关键技术指标
            latest_data = df.iloc[-1]
            
            # 计算技术指标
            rsi = latest_data.get('RSI')
            price = latest_data.get('Close')
            price_change = latest_data.get('Change')
            
            # 确定MA趋势
            ma_trend = 'UP' if latest_data.get('MA5', 0) > latest_data.get('MA20', 0) else 'DOWN'
            
            # 确定MACD信号
            macd = latest_data.get('MACD', 0)
            macd_signal = latest_data.get('MACD_Signal', 0)
            macd_signal_type = 'BUY' if macd > macd_signal else 'SELL'
            
            # 确定成交量状态
            volume_ratio = latest_data.get('Volume_Ratio', 1)
            volume_status = 'HIGH' if volume_ratio > 1.5 else ('LOW' if volume_ratio < 0.5 else 'NORMAL')
            
            # AI 分析内容
            # 最近14天的股票数据记录
            recent_data = df.tail(14).to_dict('records')
            
            # 包含trend, volatility, volume_trend, rsi_level的字典
            technical_summary = {
                'trend': 'upward' if df.iloc[-1]['MA5'] > df.iloc[-1]['MA20'] else 'downward',
                'volatility': f"{df.iloc[-1]['Volatility']:.2f}%",
                'volume_trend': 'increasing' if df.iloc[-1]['Volume_Ratio'] > 1 else 'decreasing',
                'rsi_level': df.iloc[-1]['RSI']
            }
            
            # 根据市场类型调整分析提示
            base_prompt = f"你是一个专业的股票分析师。请对 **{name_display}** 进行深入的技术分析。"
            
            if market_type in ['ETF', 'LOF']:
                prompt = f"""
                {base_prompt}
                分析基金 {name_display}：

                技术指标概要：
                {technical_summary}
                
                近14日交易数据：
                {recent_data}
                
                请提供：
                1. 净值走势分析（包含支撑位和压力位）
                2. 成交量分析及其对净值的影响
                3. 风险评估（包含波动率和折溢价分析）
                4. 短期和中期净值预测
                5. 关键价格位分析
                6. 申购赎回建议（包含止损位）
                
                请基于技术指标和市场表现进行分析，给出具体数据支持。
                """
            elif market_type == 'US':
                prompt = f"""
                {base_prompt}
                分析美股 {name_display}：

                技术指标概要：
                {technical_summary}
                
                近14日交易数据：
                {recent_data}
                
                请提供：
                1. 趋势分析（包含支撑位和压力位，美元计价）
                2. 成交量分析及其含义
                3. 风险评估（包含波动率和美股市场特有风险）
                4. 短期和中期目标价位（美元）
                5. 关键技术位分析
                6. 具体交易建议（包含止损位）
                
                请基于技术指标和美股市场特点进行分析，给出具体数据支持。
                """
            elif market_type == 'HK':
                prompt = f"""
                {base_prompt}
                分析港股 {name_display}：

                技术指标概要：
                {technical_summary}
                
                近14日交易数据：
                {recent_data}
                
                请提供：
                1. 趋势分析（包含支撑位和压力位，港币计价）
                2. 成交量分析及其含义
                3. 风险评估（包含波动率和港股市场特有风险）
                4. 短期和中期目标价位（港币）
                5. 关键技术位分析
                6. 具体交易建议（包含止损位）
                
                请基于技术指标和港股市场特点进行分析，给出具体数据支持。
                """
            else:  # A股
                prompt = f"""
                {base_prompt}
                分析A股 {name_display}：

                技术指标概要：
                {technical_summary}
                
                近14日交易数据：
                {recent_data}
                
                请提供：
                1. 趋势分析（包含支撑位和压力位）
                2. 成交量分析及其含义
                3. 风险评估（包含波动率分析）
                4. 短期和中期目标价位
                5. 关键技术位分析
                6. 具体交易建议（包含止损位）
                
                请基于技术指标和A股市场特点进行分析，给出具体数据支持。
                """
            
            # 格式化API URL
            api_url = APIUtils.format_api_url(self.API_URL)
            
            # 准备请求数据
            request_data = {
                "model": self.API_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "stream": stream
            }
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY}"
            }
            
            # 获取当前日期作为分析日期
            analysis_date = datetime.now().strftime("%Y-%m-%d")
            
            # 异步请求API
            async with httpx.AsyncClient(timeout=self.API_TIMEOUT) as client:
                # 记录请求
                logger.debug(f"发送AI请求: URL={api_url}, MODEL={self.API_MODEL}, STREAM={stream}")
                
                # 先发送技术指标数据
                yield json.dumps({
                    "stock_code": stock_code,
                    "status": "analyzing",
                    "rsi": rsi,
                    "price": price,
                    "price_change": price_change,
                    "ma_trend": ma_trend,
                    "macd_signal": macd_signal_type,
                    "volume_status": volume_status,
                    "analysis_date": analysis_date
                })
                
                if stream:
                    # 流式响应处理
                    async with client.stream("POST", api_url, json=request_data, headers=headers) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            error_data = json.loads(error_text)
                            error_message = error_data.get('error', {}).get('message', '未知错误')
                            logger.error(f"AI API请求失败: {response.status_code} - {error_message}")
                            yield json.dumps({
                                "stock_code": stock_code,
                                "error": f"API请求失败: {error_message}",
                                "status": "error"
                            })
                            return
                            
                        # 处理流式响应
                        buffer = ""
                        collected_messages = []
                        chunk_count = 0
                        
                        async for chunk in response.aiter_text():
                            if chunk:
                                lines = chunk.strip().split('\n')
                                for raw_line in lines:
                                    line = raw_line.strip()
                                    if not line:
                                        continue

                                    # 确保统一去除 data: 前缀
                                    while line.startswith("data: "):
                                        line = line[len("data: "):]

                                    if line == "[DONE]":
                                        logger.debug("收到流结束标记 [DONE]")
                                        continue

                                    try:
                                        chunk_data = json.loads(line)

                                        # 检查是否有 finish_reason（一般是最后一次标记）
                                        finish_reason = chunk_data.get("choices", [{}])[0].get("finish_reason")
                                        if finish_reason == "stop":
                                            logger.debug("收到 finish_reason=stop，流结束")
                                            continue

                                        # 解析 delta
                                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                                        content = delta.get("content")
                                        
                                        # 过滤 None 和空字符串
                                        if content is None or content == "":
                                            continue

                                        logger.info(f"AI返回delta内容: {content}")
                                        
                                        chunk_count += 1
                                        buffer += content
                                        collected_messages.append(content)

                                        yield json.dumps({
                                            "stock_code": stock_code,
                                            "ai_analysis_chunk": content,
                                            "status": "analyzing"
                                        })
                                    except json.JSONDecodeError:
                                        logger.error(f"JSON解析错误，块内容: {raw_line}")
                                        if "streaming failed after retries" in raw_line.lower():
                                            logger.error("检测到流式传输失败")
                                            yield json.dumps({
                                                "stock_code": stock_code,
                                                "error": "流式传输失败，请稍后重试",
                                                "status": "error"
                                            })
                                            return
                                        continue

                        
                        logger.info(f"AI流式处理完成，共收到 {chunk_count} 个内容片段，总长度: {len(buffer)}")
                        
                        # 如果buffer不为空且不以换行符结束，发送一个换行符
                        if buffer and not buffer.endswith('\n'):
                            logger.debug("发送换行符")
                            yield json.dumps({
                                "stock_code": stock_code,
                                "ai_analysis_chunk": "\n",
                                "status": "analyzing"
                            })
                        
                        # 完整的分析内容
                        full_content = buffer
                        
                        # 使用统一评分器计算分析评分（与 StockScorer 算法一致）
                        score = self.scorer.calculate_score(df)
                        
                        # 使用统一评分器获取投资建议
                        recommendation = self.scorer.get_recommendation(score)
                        
                        # 补发完整分析内容，供前端展示
                        if full_content:
                            yield json.dumps({
                                "stock_code": stock_code,
                                "analysis": full_content,
                                "status": "completed"
                                
                            })
                        
                        # 发送完成状态和评分、建议
                        yield json.dumps({
                            "stock_code": stock_code,
                            "status": "completed",
                            "score": score,
                            "recommendation": recommendation
                        })
                else:
                    # 非流式响应处理
                    response = await client.post(api_url, json=request_data, headers=headers)
                    
                    if response.status_code != 200:
                        error_data = response.json()
                        error_message = error_data.get('error', {}).get('message', '未知错误')
                        logger.error(f"AI API请求失败: {response.status_code} - {error_message}")
                        yield json.dumps({
                            "stock_code": stock_code,
                            "error": f"API请求失败: {error_message}",
                            "status": "error"
                        })
                        return
                    
                    response_data = response.json()
                    analysis_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # 使用统一评分器计算分析评分（与 StockScorer 算法一致）
                    score = self.scorer.calculate_score(df)
                    
                    # 使用统一评分器获取投资建议
                    recommendation = self.scorer.get_recommendation(score)
                    
                    # 发送完整的分析结果
                    yield json.dumps({
                        "stock_code": stock_code,
                        "status": "completed",
                        "analysis": analysis_text,
                        "score": score,
                        "recommendation": recommendation,
                        "rsi": rsi,
                        "price": price,
                        "price_change": price_change,
                        "ma_trend": ma_trend,
                        "macd_signal": macd_signal_type,
                        "volume_status": volume_status,
                        "analysis_date": analysis_date
                    })
                    
        except Exception as e:
            logger.error(f"AI分析出错: {str(e)}", exc_info=True)
            yield json.dumps({
                "stock_code": stock_code,
                "error": f"分析出错: {str(e)}",
                "status": "error"
            })
            
    def _extract_recommendation(self, analysis_text: str) -> str:
        """从分析文本中提取投资建议"""
        # 查找投资建议部分
        investment_advice_pattern = r"##\s*投资建议\s*\n(.*?)(?:\n##|\Z)"
        match = re.search(investment_advice_pattern, analysis_text, re.DOTALL)
        
        if match:
            advice_text = match.group(1).strip()
            
            # 提取关键建议
            if "买入" in advice_text or "增持" in advice_text:
                return "买入"
            elif "卖出" in advice_text or "减持" in advice_text:
                return "卖出"
            elif "持有" in advice_text:
                return "持有"
            else:
                return "观望"
        
        return "观望"  # 默认建议
        
    def _calculate_analysis_score(self, analysis_text: str, technical_summary: dict) -> int:
        """计算分析评分"""
        score = 50  # 基础分数
        
        # 根据技术指标调整分数
        if technical_summary['trend'] == 'upward':
            score += 10
        else:
            score -= 10
            
        if technical_summary['volume_trend'] == 'increasing':
            score += 5
        else:
            score -= 5
            
        rsi = technical_summary['rsi_level']
        if rsi < 30:  # 超卖
            score += 15
        elif rsi > 70:  # 超买
            score -= 15
            
        # 根据分析文本中的关键词调整分数
        if "强烈买入" in analysis_text or "显著上涨" in analysis_text:
            score += 20
        elif "买入" in analysis_text or "看涨" in analysis_text:
            score += 10
        elif "强烈卖出" in analysis_text or "显著下跌" in analysis_text:
            score -= 20
        elif "卖出" in analysis_text or "看跌" in analysis_text:
            score -= 10
            
        # 确保分数在0-100范围内
        return max(0, min(100, score))
    
    def _truncate_json_for_logging(self, json_obj, max_length=500):
        """
        截断JSON对象以便记录日志
        
        Args:
            json_obj: JSON对象
            max_length: 最大长度
            
        Returns:
            截断后的字符串
        """
        json_str = json.dumps(json_obj, ensure_ascii=False)
        if len(json_str) <= max_length:
            return json_str
        return json_str[:max_length] + "..." 