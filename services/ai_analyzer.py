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
            
            # 生成 Analysis V1 格式的 prompt
            from datetime import datetime
            analysis_date = datetime.now().isoformat()
            
            # 计算关键价格位
            ma5 = latest_data.get('MA5', price)
            ma20 = latest_data.get('MA20', price)
            ma60 = latest_data.get('MA60', price)
            ma200 = latest_data.get('MA200', price)
            
            # 构建 Analysis V1 prompt（统一格式，适用所有市场）
            market_name_map = {'A': 'A股', 'HK': '港股', 'US': '美股', 'ETF': 'ETF', 'LOF': 'LOF'}
            market_display = market_name_map.get(market_type, market_type)
            
            prompt = f"""
你是一个专业的股票技术分析师。请对 {market_display} **{name_display}** 进行深入的结构化分析，并严格按照 JSON schema 格式输出。

**核心原则：**
1. 只进行结构分析，不做走势预测
2. 不提供买卖建议、目标价
3. 提供详细、深入的技术分析，帮助投资者理解当前市场结构
4. 判断区只提供结构前提的候选项，让用户自己判断
5. 必须严格使用指定的枚举值

**枚举值说明（必须严格遵守）：**
- structure_type: "uptrend" | "downtrend" | "consolidation"
- ma200_position: "above" | "below" | "near" | "no_data"
- phase: "early" | "middle" | "late" | "unclear"
- pattern_type: "head_shoulders" | "double_top_bottom" | "triangle" | "channel" | "wedge" | "flag" | "none"
- signal: "strengthening" | "weakening" | "extreme" | "neutral"
- risk_level: "high" | "medium" | "low"
- option_type: "structure_premise" | "execution_method" | "risk_check"

**股票信息：**
- 代码：{stock_code}
- 名称：{stock_name}
- 当前价格：{price:.2f}
- MA5: {ma5:.2f}, MA20: {ma20:.2f}, MA60: {ma60:.2f}, MA200: {ma200:.2f}
- RSI: {rsi:.1f}
- 成交量状态：{volume_status}

**技术指标概要：**
{technical_summary}

**近14日交易数据：**
{recent_data}

**分析要求：**

1. **结构快照（Structure Snapshot）**：
   - 详细描述当前的趋势结构，包括均线排列、价格位置关系
   - 列出3-6个关键价格位（支撑/压力），并说明其重要性
   - trend_description 应该详细阐述当前结构的形成过程和特征

2. **形态拟合（Pattern Fitting）**：
   - 识别是否存在经典技术形态
   - 详细描述形态的特征、关键点位、完成度
   - 如果没有明显形态，说明当前价格运行的特点

3. **指标翻译（Indicator Translate）**：
   - 至少分析2-3个关键指标（RSI、MACD、成交量等）
   - 每个指标的解读要详细，包括：当前值、历史对比、结构含义
   - global_note 要综合所有指标，给出整体技术面评估

4. **误读风险（Risk of Misreading）**：
   - 详细列出可能导致结构误判的风险因素
   - 标记关键的风险信号（如背离、缩量、假突破等）
   - caution_note 要具体说明需要观察的关键点

5. **判断区（Judgment Zone）**：
   - 提供2-4个结构前提候选项，覆盖不同的结构演化路径
   - 每个候选项要详细描述触发条件、价格位、成交量要求等
   - 风险检查项要具体、可操作

**请按以下 JSON 格式输出（必须是有效的 JSON）：**

```json
{{
  "stock_code": "{stock_code}",
  "stock_name": "{stock_name}",
  "market_type": "{market_type}",
  "analysis_date": "{analysis_date}",
  "structure_snapshot": {{
    "structure_type": "uptrend|downtrend|consolidation",
    "ma200_position": "above|below|near|no_data",
    "phase": "early|middle|late|unclear",
    "key_levels": [
      {{"price": 12.00, "label": "支撑位1"}},
      {{"price": 11.50, "label": "支撑位2(MA200)"}},
      {{"price": 12.80, "label": "压力位1"}}
    ],
    "trend_description": "详细描述当前趋势结构，包括均线排列、价格运行特征、结构强弱等"
  }},
  "pattern_fitting": {{
    "pattern_type": "head_shoulders|double_top_bottom|triangle|channel|wedge|flag|none",
    "pattern_description": "详细描述形态特征、关键点位、完成度、可能的演化方向",
    "completion_rate": 65
  }},
  "indicator_translate": {{
    "indicators": [
      {{
        "name": "RSI(14)",
        "value": "55",
        "signal": "strengthening|weakening|extreme|neutral",
        "interpretation": "详细解读RSI指标，包括当前值的含义、历史对比、结构信号"
      }},
      {{
        "name": "MACD",
        "value": "DIF: 0.05, DEA: 0.03",
        "signal": "strengthening|weakening|extreme|neutral",
        "interpretation": "详细分析MACD指标，包括金叉/死叉、柱状图变化、动能强弱"
      }},
      {{
        "name": "成交量",
        "value": "1.2倍均量",
        "signal": "strengthening|weakening|extreme|neutral",
        "interpretation": "详细分析成交量变化，包括量价配合、资金流向、市场情绪"
      }}
    ],
    "global_note": "综合所有技术指标，给出整体技术面评估，包括多空力量对比、结构稳定性等"
  }},
  "risk_of_misreading": {{
    "risk_level": "high|medium|low",
    "risk_factors": [
      "详细描述风险因素1，包括具体的价格位、指标信号等",
      "详细描述风险因素2，说明可能导致误判的情况",
      "详细描述风险因素3，提示需要关注的关键变化"
    ],
    "risk_flags": ["背离", "缩量", "假突破"],
    "caution_note": "详细说明需要特别注意的事项，包括关键观察点、确认信号、防范措施等"
  }},
  "judgment_zone": {{
    "candidates": [
      {{
        "option_id": "A",
        "option_type": "structure_premise",
        "description": "详细描述结构前提A，包括触发条件（价格位、成交量、时间等）、结构特征、后续观察重点"
      }},
      {{
        "option_id": "B",
        "option_type": "structure_premise",
        "description": "详细描述结构前提B，说明与A的区别、触发条件、结构演化路径"
      }},
      {{
        "option_id": "C",
        "option_type": "structure_premise",
        "description": "详细描述结构前提C，包括破坏性条件、关键价格位、结构失效信号"
      }}
    ],
    "risk_checks": [
      "具体的风险检查项1，说明观察什么、如何确认",
      "具体的风险检查项2，包括关键指标、确认条件",
      "具体的风险检查项3，提示需要验证的信号"
    ],
    "note": "以上为结构分析，非走势预测，系统不提供买卖建议"
  }}
}}
```

**关键要求：**
1. 必须输出完整的 JSON，不要省略任何字段
2. 所有描述字段要详细、具体，提供有价值的分析内容
3. pattern_type 必须是枚举值之一
4. signal 必须是: "strengthening", "weakening", "extreme", "neutral" 之一
5. option_type 必须是: "structure_premise", "execution_method", "risk_check" 之一
6. risk_checks 必须是字符串数组，不是对象数组
7. 判断区的 candidates 至少 2 个，最多 4 个
8. 每个分析板块都要提供深入、专业的见解

**请直接输出 JSON，不要添加任何其他文字说明。**
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
                        
                        # 尝试从完整内容中提取 Analysis V1 JSON
                        analysis_v1_json = None
                        try:
                            # 移除可能的 markdown 代码块标记
                            json_str = full_content
                            if "```json" in json_str:
                                json_str = json_str.split("```json")[1].split("```")[0].strip()
                            elif "```" in json_str:
                                json_str = json_str.split("```")[1].split("```")[0].strip()
                            
                            # 尝试解析 JSON
                            analysis_v1_json = json.loads(json_str)
                            logger.info(f"成功解析 Analysis V1 JSON for {stock_code}")
                            
                            # 验证是否包含必要字段
                            required_fields = ['structure_snapshot', 'pattern_fitting', 'indicator_translate', 
                                             'risk_of_misreading', 'judgment_zone']
                            if all(field in analysis_v1_json for field in required_fields):
                                logger.info(f"Analysis V1 JSON 包含所有必要字段")
                            else:
                                logger.warning(f"Analysis V1 JSON 缺少某些字段")
                                analysis_v1_json = None
                                
                        except (json.JSONDecodeError, IndexError) as e:
                            logger.warning(f"无法解析 Analysis V1 JSON: {str(e)}, 将作为普通文本处理")
                            analysis_v1_json = None
                        
                        # 使用统一评分器计算分析评分（与 StockScorer 算法一致）
                        score = self.scorer.calculate_score(df)
                        
                        # 使用统一评分器获取投资建议
                        recommendation = self.scorer.get_recommendation(score)
                        
                        # 如果成功解析 Analysis V1 JSON，发送结构化数据
                        if analysis_v1_json:
                            yield json.dumps({
                                "stock_code": stock_code,
                                "analysis_v1": analysis_v1_json,  # 新增：Analysis V1 结构化数据
                                "analysis": full_content,  # 保留原始文本，用于降级
                                "status": "completed",
                                "score": score,
                                "recommendation": recommendation
                            })
                        else:
                            # 降级：作为普通文本处理
                            if full_content:
                                yield json.dumps({
                                    "stock_code": stock_code,
                                    "analysis": full_content,
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