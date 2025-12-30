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
你是一个客观的市场数据呈现系统。请对 {market_display} **{name_display}** 进行结构化数据整理，严格按照 JSON schema 格式输出。

**产品宪章（必须严格遵守）：**
1. 只陈述客观事实和历史数据，不做任何预测
2. 不使用结论性语言（如"强势"、"弱势"、"看涨"、"看跌"）
3. 不使用指令性语言（如"应该"、"必须"、"建议"）
4. 不暗示走势方向（如"倾向"、"可能"、"预计"）
5. 把决策权完全交给用户

**Markdown 格式要求：**
- 使用标准 Markdown 语法
- 有序列表：使用 `1. 2. 3.` 而不是 `1）2）3）`
- 无序列表：使用 `- ` 或 `* `
- 粗体：使用 `**文本**`
- 代码：使用 `` `代码` ``
- 所有描述字段都会被 Markdown 渲染，请使用规范语法

**枚举值说明（必须严格遵守）：**
- structure_type: "uptrend" | "downtrend" | "consolidation"
- ma200_position: "above" | "below" | "near" | "no_data"
- phase: "early" | "middle" | "late" | "unclear"
- pattern_type: "head_shoulders" | "double_top_bottom" | "triangle" | "channel" | "wedge" | "flag" | "none"
- signal: "strengthening" | "weakening" | "extreme" | "neutral"
- risk_level: "high" | "medium" | "low"
- option_type: "structure_premise" | "execution_method" | "risk_check"

**当前数据：**
- 代码：{stock_code}
- 名称：{stock_name}
- 当前价格：{price:.2f}
- MA5: {ma5:.2f}, MA20: {ma20:.2f}, MA60: {ma60:.2f}, MA200: {ma200:.2f}
- RSI: {rsi:.1f}
- 成交量状态：{volume_status}

**技术指标数据：**
{technical_summary}

**近14日交易数据：**
{recent_data}

**数据整理要求（附正反示例）：**

1. **结构快照（Structure Snapshot）**：
   - 陈述价格与各均线的位置关系
   - ✅ 正确："价格 11.56，位于 MA20(11.80) 下方 0.24 元，位于 MA200(11.55) 上方 0.01 元"
   - ❌ 错误："价格在 MA20 下方，处于弱势区域"
   
   - 列出3-6个关键价格位，只说明是什么位置
   - ✅ 正确："11.65（近期高点）、11.56（MA200）、11.30（近期低点）"
   - ❌ 错误:"11.65 压力位、11.30 支撑位"
   
   - trend_description 只描述客观事实
   - ✅ 正确："MA5(11.48) < MA20(11.80) < MA60(11.92)，价格在 11.30-11.65 区间运行 8 个交易日，成交量平均为 20 日均量的 0.85 倍"
   - ❌ 错误："均线空头排列，弱势整理，缩量盘整"

2. **形态拟合（Pattern Fitting）**：
   - 只描述形态的几何特征和关键点位
   - ✅ 正确："价格在 11.30-11.65 区间内形成 3 个高点（11.65, 11.62, 11.63）和 3 个低点（11.32, 11.35, 11.30），高点逐渐下降，低点基本持平"
   - ❌ 错误："形成下降三角形，即将向下突破"
   
   - 不说形态"完成"或"突破"
   - ✅ 正确："当前价格 11.56，位于 11.30-11.65 区间中部"
   - ❌ 错误："形态完成度 80%，等待突破确认"

3. **指标翻译（Indicator Translate）**：
   - 只陈述指标的当前数值和历史对比
   - ✅ 正确："RSI(14) 当前 44.50，过去 30 天均值 52.3，过去 90 天均值 48.7，过去 30 天最高 68.2，最低 35.6"
   - ❌ 错误："RSI 44.50，处于中性偏弱区域"
   
   - ✅ 正确："MACD DIF -0.05，DEA -0.03，柱状图 -0.02。过去 5 日 DIF 从 0.02 降至 -0.05，DEA 从 0.01 降至 -0.03"
   - ❌ 错误："MACD 死叉，动能转弱"
   
   - ✅ 正确："KDJ 当前 K 值 45.2，D 值 42.8，J 值 50.0。过去 5 日 K 值从 38.5 升至 45.2，D 值从 36.2 升至 42.8"
   - ❌ 错误："KDJ 金叉，即将进入强势区"
   
   - ✅ 正确："成交量今日 120 万股，20 日均量 150 万股，今日成交量为均量的 0.80 倍"
   - ❌ 错误："成交量萎缩，市场观望情绪浓厚"
   
   - global_note 只综合陈述各指标的数值状态，使用 Markdown 列表格式
   - ✅ 正确："当前指标状态：\n- RSI 44.50 低于 30 日均值 7.8 个点\n- MACD DIF 由正转负已持续 3 日\n- KDJ K 值在 50 以下区域运行\n- 成交量连续 5 日低于均量"
   - ❌ 错误："技术指标整体偏弱，多空力量对比向空方倾斜"

4. **误读风险（Risk of Misreading）**：
   - 只列出可能影响数据解读的客观因素
   - ✅ 正确："MA200(11.55) 与 MA60(11.92) 间距 0.37 元，占 MA200 的 3.2%"
   - ❌ 错误："均线粘合，容易出现假突破"
   
   - ✅ 正确："成交量连续 5 日低于 20 日均量，平均为均量的 0.75 倍"
   - ❌ 错误："缩量盘整，不宜操作"
   
   - ✅ 正确："RSI 在 40-50 区间震荡 10 个交易日，而价格下跌 3.5%"
   - ❌ 错误："RSI 与价格背离，警惕反转"
   
   - caution_note 只说明需要观察的数据点，可以包含左侧/右侧交易观察点
   - ✅ 正确："观察要点：\n- 价格是否突破 11.65 或跌破 11.30\n- 成交量是否超过 20 日均量 1.5 倍\n- **左侧交易者**：可在价格接近 11.30 时观察是否出现止跌信号\n- **右侧交易者**：等待价格突破 11.65 并放量确认后再行动"
   - ❌ 错误："需要等待放量突破确认，避免追高"

5. **判断区（Judgment Zone）**：
   - 提供2-4个结构前提候选项，只描述触发条件
   - ✅ 正确："价格突破 11.65 且成交量超过 20 日均量 1.5 倍，MA5 上穿 MA20"
   - ❌ 错误："突破后看涨，目标位 12.50"
   
   - ✅ 正确："价格在 11.30-11.65 区间震荡超过 10 个交易日，成交量维持在均量 0.7-1.2 倍"
   - ❌ 错误:"继续震荡整理，等待方向选择"
   
   - 风险检查项只列出需要观察的数据点
   - ✅ 正确："观察成交量是否超过 20 日均量 1.5 倍"
   - ❌ 错误："必须放量突破才能确认有效性"

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
        "value": "44.50",
        "signal": "strengthening|weakening|extreme|neutral",
        "interpretation": "RSI 当前 44.50，过去 30 天均值 52.3，过去 90 天均值 48.7，过去 30 天最高 68.2，最低 35.6"
      }},
      {{
        "name": "MACD",
        "value": "DIF: -0.05, DEA: -0.03, 柱状图: -0.02",
        "signal": "strengthening|weakening|extreme|neutral",
        "interpretation": "MACD DIF -0.05，DEA -0.03，柱状图 -0.02。过去 5 日 DIF 从 0.02 降至 -0.05，DEA 从 0.01 降至 -0.03"
      }},
      {{
        "name": "KDJ",
        "value": "K: 45.2, D: 42.8, J: 50.0",
        "signal": "strengthening|weakening|extreme|neutral",
        "interpretation": "KDJ 当前 K 值 45.2，D 值 42.8，J 值 50.0。过去 5 日 K 值从 38.5 升至 45.2，D 值从 36.2 升至 42.8"
      }},
      {{
        "name": "成交量",
        "value": "120万股（均量的0.80倍）",
        "signal": "strengthening|weakening|extreme|neutral",
        "interpretation": "成交量今日 120 万股，20 日均量 150 万股，今日成交量为均量的 0.80 倍，连续 5 日低于均量"
      }}
    ],
    "global_note": "RSI 44.50 低于 30 日均值 7.8 个点，MACD DIF 由正转负已持续 3 日，KDJ K 值在 50 以下区域运行，成交量连续 5 日低于均量"
  }},
  "risk_of_misreading": {{
    "risk_level": "high|medium|low",
    "risk_factors": [
      "陈述客观因素1，如'MA200 与 MA60 间距 1.8%，均线粘合'",
      "陈述客观因素2，如'成交量连续 3 日低于 20 日均量 25%'",
      "陈述客观因素3，如'RSI 与价格出现背离，RSI 上升而价格下降'"
    ],
    "risk_flags": ["背离", "缩量", "均线粘合"],
    "caution_note": "列出需要观察的数据点，如'观察 MA200 是否有效突破，成交量是否配合放大'"
  }},
  "judgment_zone": {{
    "candidates": [
      {{
        "option_id": "A",
        "option_type": "structure_premise",
        "description": "价格突破 12.50 且成交量超过 20 日均量 1.5 倍，MA5 上穿 MA20"
      }},
      {{
        "option_id": "B",
        "option_type": "structure_premise",
        "description": "价格在 11.80-12.20 区间震荡超过 5 个交易日，成交量维持在均量 0.8-1.2 倍"
      }},
      {{
        "option_id": "C",
        "option_type": "structure_premise",
        "description": "价格跌破 11.50 且成交量超过 20 日均量 1.3 倍，MA5 下穿 MA20"
      }}
    ],
    "risk_checks": [
      "观察成交量是否超过 20 日均量 1.5 倍",
      "观察 RSI 是否进入超买区（>70）或超卖区（<30）",
      "观察价格是否有效站稳 MA200"
    ],
    "note": "以上为数据呈现，非走势预测，系统不提供买卖建议"
  }}
}}
```


**关键要求：**
1. 必须输出完整的 JSON，不要省略任何字段
2. 所有描述字段只陈述客观事实和数据，不做评估或预测
3. 不使用"强势"、"弱势"、"看涨"、"看跌"等结论性词汇
4. 不使用"应该"、"必须"、"建议"等指令性词汇
5. pattern_type 必须是枚举值之一
6. signal 必须是: "strengthening", "weakening", "extreme", "neutral" 之一
7. option_type 必须是: "structure_premise", "execution_method", "risk_check" 之一
8. risk_checks 必须是字符串数组，只列出观察项，不给建议
9. 判断区的 candidates 至少 2 个，最多 4 个，只描述触发条件
10. 把决策权完全交给用户，系统只提供数据

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