import pandas as pd
from typing import Dict, List, Tuple
from utils.logger import get_logger

# 获取日志器
logger = get_logger()

class StockScorer:
    """
    股票评分服务
    负责根据技术指标计算股票的综合评分
    """
    
    def __init__(self):
        """初始化股票评分服务"""
        logger.debug("初始化StockScorer股票评分服务")
    
    def calculate_score(self, df: pd.DataFrame) -> int:
        """
        计算股票评分（满分100分）
        更加细致地评估技术面状态
        """
        try:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            score = 0
            
            # 1. 均线系统评分 (30分) - 趋势强度
            ma5, ma20, ma60 = latest['MA5'], latest['MA20'], latest['MA60']
            close = latest['Close']
            
            if ma5 > ma20 > ma60: # 多头排列
                score += 30
            elif close > ma5 > ma20: # 股价站上短期均线且排布尚可
                score += 25
            elif close > ma20: # 股价站稳中线
                score += 15
            elif ma5 > ma20: # 均线金叉
                score += 10
            elif close < ma20 < ma60: # 空头趋势
                score += 0
            else:
                score += 5 # 默认分
                
            # 2. RSI 相对强弱 (20分) - 超买超卖与蓄势
            rsi = latest['RSI']
            if 50 <= rsi <= 65: # 强势区域
                score += 20
            elif 40 <= rsi < 50: # 蓄势区域
                score += 15
            elif 65 < rsi <= 80: # 超买预警
                score += 10
            elif rsi < 30: # 严重超卖，可能反弹
                score += 12
            elif rsi > 80: # 严重超买，风险极高
                score += 3
            else:
                score += 5
                
            # 3. MACD 指标 (20分) - 动力方向
            macd, signal, hist = latest['MACD'], latest['Signal'], latest['Histogram']
            prev_hist = prev['Histogram']
            
            if macd > 0 and signal > 0 and macd > signal: # 强势区金叉
                score += 20
            elif macd > signal: # 普通金叉
                score += 15
            elif hist > prev_hist: # 能量柱增长 (动力增强)
                score += 10
            elif macd < signal: # 死叉
                score += 0
            else:
                score += 5
                
            # 4. 成交量配合 (20分) - 意愿强度
            vol_ratio = latest['Volume_Ratio']
            if 1.5 < vol_ratio < 3.0: # 且不过分放量
                score += 20
            elif 1.0 < vol_ratio <= 1.5: # 稳步放量
                score += 15
            elif vol_ratio > 4.0: # 天量，风险增加
                score += 5
            elif vol_ratio < 0.5: # 缩量
                score += 5
            else:
                score += 10
                
            # 5. 波动率与位置 (10分) - 风险补偿
            volatility = latest.get('Volatility', 5)
            if volatility < 5: # 低波稳健
                score += 10
            elif volatility < 10:
                score += 7
            else:
                score += 3
                
            # 最终分数修正
            return min(max(int(score), 0), 100)
            
        except Exception as e:
            logger.error(f"计算评分时出错: {str(e)}")
            logger.exception(e)
            raise
            
    def get_recommendation(self, score: int) -> str:
        """
        根据评分获取投资建议
        
        Args:
            score: 股票评分（0-100）
            
        Returns:
            投资建议文本
        """
        if score >= 80:
            return "强烈推荐"
        elif score >= 70:
            return "推荐"
        elif score >= 60:
            return "谨慎推荐"
        elif score >= 40:
            return "观望"
        elif score >= 20:
            return "不推荐"
        else:
            return "强烈不推荐"
            
    def batch_score_stocks(self, stock_dfs: Dict[str, pd.DataFrame]) -> List[Tuple[str, int, str]]:
        """
        批量评分多只股票
        
        Args:
            stock_dfs: 字典，键为股票代码，值为DataFrame
            
        Returns:
            评分结果列表，每项为(股票代码, 评分, 推荐)的三元组
        """
        results = []
        
        for stock_code, df in stock_dfs.items():
            try:
                score = self.calculate_score(df)
                recommendation = self.get_recommendation(score)
                results.append((stock_code, score, recommendation))
            except Exception as e:
                logger.error(f"评分股票 {stock_code} 时出错: {str(e)}")
                
        # 按评分降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results 