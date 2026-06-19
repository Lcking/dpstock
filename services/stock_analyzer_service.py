import json
import math
import asyncio
import math
from copy import deepcopy
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


def _json_safe(value: Any) -> Any:
    """递归清洗 NaN/Inf，确保输出为标准 JSON。"""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    return value


def _safe_dumps(value: Any, ensure_ascii: bool = False) -> str:
    """统一 JSON 序列化入口，避免 NaN/Inf 进入响应流。"""
    return json.dumps(_json_safe(value), ensure_ascii=ensure_ascii, allow_nan=False)


def _normalize_turnover_rate(value: Any) -> Optional[float]:
    """将原始换手率标准化为可展示的百分比值。"""
    if value is None:
        return None
    try:
        if hasattr(value, "item"):
            value = value.item()
        turnover = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(turnover) or turnover <= 0:
        return None
    return round(turnover, 2)


def _sanitize_for_json(obj: Any) -> Any:
    """将 NaN/Inf 等无法被标准 JSON 表示的浮点值转为 None，避免前端 JSON.parse 失败。"""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, (str,)):
        return obj
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    try:
        f = float(obj)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return obj


def _build_turnover_profile(turnover_rate: Optional[float]) -> Optional[Dict[str, str]]:
    """基于换手率生成简短热度解读。"""
    if turnover_rate is None:
        return None

    if turnover_rate < 1:
        return {
            "tag": "低活跃",
            "signal": "weakening",
            "interpretation": f"换手率 {turnover_rate:.2f}%，筹码交换偏慢，短线关注度有限。",
        }
    if turnover_rate < 3:
        return {
            "tag": "正常活跃",
            "signal": "neutral",
            "interpretation": f"换手率 {turnover_rate:.2f}%，交易热度处于常见区间，关注度较为正常。",
        }
    if turnover_rate < 8:
        return {
            "tag": "高活跃",
            "signal": "strengthening",
            "interpretation": f"换手率 {turnover_rate:.2f}%，筹码交换较快，市场关注度明显提升。",
        }
    return {
        "tag": "极高活跃",
        "signal": "extreme",
        "interpretation": f"换手率 {turnover_rate:.2f}%，交易非常活跃，短线博弈特征更强。",
    }


def _compute_volume_ratio_5d(df_with_indicators: Any) -> Optional[float]:
    """
    计算 5 日量比 = 当日成交量 / 过去 5 日成交量均值。
    严格区别于 technical_indicator 里 20 日窗口的 Volume_Ratio——老法师口径是 5 日。
    需要至少 6 行数据；不足或非有限值返回 None。
    """
    try:
        if df_with_indicators is None or len(df_with_indicators) < 6:
            return None
        if 'Volume' not in df_with_indicators.columns:
            return None

        today_volume = float(df_with_indicators['Volume'].iloc[-1])
        prev5_mean = float(df_with_indicators['Volume'].iloc[-6:-1].mean())

        if not math.isfinite(today_volume) or not math.isfinite(prev5_mean) or prev5_mean <= 0:
            return None

        ratio = today_volume / prev5_mean
        if not math.isfinite(ratio) or ratio <= 0:
            return None
        return round(ratio, 2)
    except Exception:
        return None


def _build_heat_signal(
    turnover_rate: Optional[float],
    volume_ratio_5d: Optional[float],
) -> Optional[Dict[str, str]]:
    """
    基于"量比 + 换手率"组合生成热度标签。
    经验法则（来源：A 股短线圈量价分析），对中小盘 / 题材股阈值合理，
    对大盘蓝筹（换手日常 <1%）几乎不会触发，仅供参考。

    规则优先级：见顶 > 加速 > 启动 > 量价背离 > 无信号
    """
    if turnover_rate is None or volume_ratio_5d is None:
        return None

    t = turnover_rate
    v = volume_ratio_5d

    if t > 10 and v > 5:
        return {
            "tag": "见顶预警",
            "signal": "extreme",
            "interpretation": (
                f"换手率 {t:.2f}% 且 5 日量比 {v:.2f}，量能与筹码交换都达到极端水平，"
                f"经验上对应行情末端：手中有仓位逢高减、空仓不要追高。"
            ),
            "action_hint": "低跟高跑",
        }
    if 5 <= t <= 10 and 3 <= v <= 5:
        return {
            "tag": "加速",
            "signal": "strengthening",
            "interpretation": (
                f"换手率 {t:.2f}%、5 日量比 {v:.2f}，资金涌入与筹码交换同步放大，"
                f"对应主升浪进行时；位置不一定低，留意是否已经吃过一段。"
            ),
            "action_hint": "持有为主，不轻易追高",
        }
    if t > 5 and 2 <= v < 3:
        return {
            "tag": "启动",
            "signal": "strengthening",
            "interpretation": (
                f"换手率 {t:.2f}%、5 日量比 {v:.2f}，热度刚起来但量能尚未失控，"
                f"经验上对应行情起步阶段，但要确认是否有基本面 / 板块共振。"
            ),
            "action_hint": "可关注",
        }
    if t > 5 and v < 2:
        return {
            "tag": "量价背离",
            "signal": "weakening",
            "interpretation": (
                f"换手率 {t:.2f}% 不低，但 5 日量比仅 {v:.2f}，"
                f"说明筹码在换手却没有新增量能进场——典型的接力资金断档信号，警惕回调。"
            ),
            "action_hint": "止盈 / 离场",
        }
    return None


def _augment_analysis_v1_with_heat(
    analysis_v1: Optional[Dict[str, Any]],
    turnover_rate: Optional[float],
    volume_ratio_5d: Optional[float],
) -> Optional[Dict[str, Any]]:
    """向 Analysis V1 指标翻译区追加 量比 + 量价共振 标签。"""
    if not isinstance(analysis_v1, dict):
        return analysis_v1

    if volume_ratio_5d is None:
        return analysis_v1

    data = deepcopy(analysis_v1)
    indicator_translate = data.setdefault("indicator_translate", {})
    indicators = indicator_translate.setdefault("indicators", [])

    # 量比指标项（独立于换手率，单独展示）
    vr_item = {
        "name": "量比(5日)",
        "value": f"{volume_ratio_5d:.2f}",
        "signal": (
            "strengthening" if volume_ratio_5d >= 2
            else "weakening" if volume_ratio_5d < 0.8
            else "neutral"
        ),
        "interpretation": (
            f"量比 {volume_ratio_5d:.2f}：当日成交量约为过去 5 日均量的 {volume_ratio_5d:.2f} 倍。"
            f"≥2 视为放量，<0.8 视为缩量；放量需结合换手率判断是真热还是诱多。"
        ),
    }

    # 热度标签（量比 + 换手率组合）
    heat_signal = _build_heat_signal(turnover_rate, volume_ratio_5d)
    heat_item = None
    if heat_signal is not None:
        heat_item = {
            "name": "量价共振",
            "value": heat_signal["tag"],
            "signal": heat_signal["signal"],
            "interpretation": (
                f"{heat_signal['interpretation']} 操作建议：{heat_signal.get('action_hint', '—')}。"
                f"（经验法则，对中小盘 / 题材股阈值合理；大盘蓝筹换手天然较低，几乎不会触发，仅供参考）"
            ),
        }

    # 追加或替换
    def _upsert(name: str, item: Optional[Dict[str, Any]]) -> None:
        if item is None:
            return
        for idx, existing in enumerate(indicators):
            if existing.get("name") == name:
                indicators[idx] = item
                return
        indicators.append(item)

    _upsert("量比(5日)", vr_item)
    _upsert("量价共振", heat_item)

    return data


def _augment_analysis_v1_with_turnover(
    analysis_v1: Optional[Dict[str, Any]],
    turnover_rate: Optional[float],
) -> Optional[Dict[str, Any]]:
    """向 Analysis V1 的指标翻译区补充换手率指标。"""
    if not isinstance(analysis_v1, dict):
        return analysis_v1

    profile = _build_turnover_profile(turnover_rate)
    if profile is None:
        return analysis_v1

    data = deepcopy(analysis_v1)
    indicator_translate = data.setdefault("indicator_translate", {})
    indicators = indicator_translate.setdefault("indicators", [])

    turnover_item = {
        "name": "换手率",
        "value": f"{turnover_rate:.2f}%",
        "signal": profile["signal"],
        "interpretation": (
            f"{profile['interpretation']} 它更偏向反映个股热度，不等同于资金净流入或主力净买入。"
        ),
    }

    replaced = False
    for idx, indicator in enumerate(indicators):
        if indicator.get("name") == "换手率":
            indicators[idx] = turnover_item
            replaced = True
            break

    if not replaced:
        indicators.append(turnover_item)

    existing_note = indicator_translate.get("global_note") or ""
    turnover_note = (
        f"- 换手率 {turnover_rate:.2f}%：{profile['tag']}，主要反映交易热度，不直接代表资金流入方向"
    )
    if turnover_note not in existing_note:
        indicator_translate["global_note"] = (
            f"{existing_note.rstrip()}\n{turnover_note}".strip()
            if existing_note
            else turnover_note
        )

    return data


def _build_archive_content(
    analysis_v1: Optional[Dict[str, Any]],
    fallback_content: str,
) -> str:
    """归档文章优先保存增强后的 Analysis V1，旧链路则回退到原始文本。"""
    if isinstance(analysis_v1, dict):
        try:
            return json.dumps(analysis_v1, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[Archive] Failed to serialize analysis_v1 content: {e}")
    return fallback_content

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

            # 如果名称为空（快速路径跳过了列表查询），尝试补全
            if not stock_name and market_type == 'A':
                stock_name = await asyncio.to_thread(
                    self.data_provider.lookup_stock_name,
                    stock_code,
                    True,
                )
                if stock_name:
                    logger.info(f"补全股票名称: {stock_code} -> {stock_name}")
            
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

            turnover_rate = _normalize_turnover_rate(latest_data.get('Turnover'))
            turnover_profile = _build_turnover_profile(turnover_rate)

            # 量比（5 日口径）+ 量价共振标签
            volume_ratio_5d = _compute_volume_ratio_5d(df_with_indicators)
            heat_signal = _build_heat_signal(turnover_rate, volume_ratio_5d)

            # 当前分析日期
            analysis_date = datetime.now().strftime('%Y-%m-%d')
            from services.data_provenance import build_data_provenance

            provenance = build_data_provenance(market_type, df_with_indicators)
            
            # 生成基本分析结果
            basic_result = {
                "stock_code": stock_code,
                "name": stock_name,  # 添加股票名称
                "market_type": market_type,
                "analysis_date": analysis_date,
                **provenance,
                "score": score,
                "price": latest_data['Close'],
                "price_change": price_change_value,  # 涨跌额 (绝对值)
                "change_percent": change_percent,  # 涨跌幅 (%)
                "ma_trend": ma_trend,
                "rsi": latest_data.get('RSI', 0),
                "macd_signal": macd_signal,
                "volume_status": volume_status,
                "turnover_rate": turnover_rate,
                "turnover_profile": turnover_profile,
                "volume_ratio_5d": volume_ratio_5d,
                "heat_signal": heat_signal,
                "recommendation": recommendation,
                "ai_analysis": ""
            }
            
            # 输出基本分析结果
            logger.info(f"基本分析结果: {_safe_dumps(basic_result)}")
            yield _safe_dumps(basic_result)
            
            # 使用AI进行深入分析
            full_analysis = ""
            ai_score = None
            analysis_v1 = None
            async for analysis_chunk in self.ai_analyzer.get_ai_analysis(df_with_indicators, stock_code, stock_name, market_type, stream):
                outgoing_chunk = analysis_chunk
                if stream:
                    # 尝试从片段中提取纯文本 (如果 ai_analyzer 返回的是 JSON 字符串片段)
                    try:
                        chunk_data = json.loads(analysis_chunk)
                        if "ai_analysis_chunk" in chunk_data:
                            full_analysis += chunk_data["ai_analysis_chunk"]
                        elif "analysis" in chunk_data:
                            full_analysis = chunk_data["analysis"]
                        if "ai_score" in chunk_data:
                            ai_score = chunk_data.get("ai_score")
                        if "analysis_v1" in chunk_data:
                            analysis_v1 = _augment_analysis_v1_with_turnover(
                                chunk_data.get("analysis_v1"),
                                turnover_rate,
                            )
                            analysis_v1 = _augment_analysis_v1_with_heat(
                                analysis_v1,
                                turnover_rate,
                                volume_ratio_5d,
                            )
                            chunk_data["analysis_v1"] = analysis_v1
                            outgoing_chunk = _safe_dumps(chunk_data, ensure_ascii=False)
                        if chunk_data.get("status") == "completed":
                            chunk_data["turnover_rate"] = turnover_rate
                            chunk_data["turnover_profile"] = turnover_profile
                            chunk_data["volume_ratio_5d"] = volume_ratio_5d
                            chunk_data["heat_signal"] = heat_signal
                            outgoing_chunk = _safe_dumps(chunk_data, ensure_ascii=False)
                    except:
                        pass
                else:
                    # 非流式直接就是完整 JSON
                    try:
                        chunk_data = json.loads(analysis_chunk)
                        full_analysis = chunk_data.get("analysis", "")
                        ai_score = chunk_data.get("ai_score")
                        analysis_v1 = _augment_analysis_v1_with_turnover(
                            chunk_data.get("analysis_v1"),
                            turnover_rate,
                        )
                        analysis_v1 = _augment_analysis_v1_with_heat(
                            analysis_v1,
                            turnover_rate,
                            volume_ratio_5d,
                        )
                        if analysis_v1 is not None:
                            chunk_data["analysis_v1"] = analysis_v1
                        chunk_data["turnover_rate"] = turnover_rate
                        chunk_data["turnover_profile"] = turnover_profile
                        chunk_data["volume_ratio_5d"] = volume_ratio_5d
                        chunk_data["heat_signal"] = heat_signal
                        outgoing_chunk = _safe_dumps(chunk_data, ensure_ascii=False)
                    except:
                        pass
                
                yield outgoing_chunk
            
            # 分析完成后，自动归档为文章
            if full_analysis:
                # 动态获取品类名称
                category_map = {'A': '股票', 'HK': '股票', 'US': '股票', 'ETF': 'ETF', 'LOF': 'LOF'}
                category_name = category_map.get(market_type, '股票')
                name_part = f"{stock_name} " if stock_name else ""
                title = f"{datetime.now().strftime('%Y年%m月%d日')} {name_part}{stock_code} {category_name}行情走势异动分析"
                score_version = None
                ai_score_json = None
                overall_score = score
                if isinstance(ai_score, dict):
                    try:
                        overall_score = int(ai_score.get("overall", {}).get("score", score))
                        score_version = str(ai_score.get("version", "1.0.0"))
                        ai_score_json = json.dumps(ai_score, ensure_ascii=False)
                    except Exception as e:
                        logger.warning(f"[Archive] Failed to serialize ai_score for {stock_code}: {e}")
                article_data = {
                    "title": title,
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "market_type": market_type,
                    "content": _build_archive_content(analysis_v1, full_analysis),
                    "score": overall_score,
                    "legacy_score": score,
                    "score_version": score_version,
                    "ai_score_json": ai_score_json,
                    "publish_date": analysis_date
                }
                await self.archive_service.save_article(article_data)
                logger.info(f"文章已自动归档: {title}, 评分: {overall_score} (legacy={score})")
                
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
