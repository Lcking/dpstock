"""
形态检测算法服务
基于价格拐点（Swing Point）检测经典技术形态，为 LLM 提供结构化的形态识别数据。

支持的形态：
- 金叉/死叉（MA 交叉）
- 双顶/双底
- 头肩顶/头肩底
- 三角形（对称、上升、下降）
- 通道（上升、下降、水平）
- 楔形（上升、下降）
- 旗形/矩形整理
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from utils.logger import get_logger

logger = get_logger()


@dataclass
class SwingPoint:
    """价格拐点"""
    index: int
    date: str
    price: float
    type: str  # 'high' or 'low'


@dataclass
class CrossoverSignal:
    """均线交叉信号"""
    date: str
    cross_type: str  # 'golden_cross' or 'death_cross'
    fast_ma: str
    slow_ma: str
    price_at_cross: float


@dataclass
class PatternResult:
    """单个形态检测结果"""
    pattern_type: str
    confidence: float  # 0-100
    description: str
    key_points: List[dict] = field(default_factory=list)
    completion_rate: int = 0


@dataclass
class PatternDetectionReport:
    """完整的形态检测报告"""
    swing_highs: List[SwingPoint]
    swing_lows: List[SwingPoint]
    crossovers: List[CrossoverSignal]
    patterns: List[PatternResult]
    summary: str


class PatternDetector:
    """
    技术形态检测器
    使用 Swing Point 拐点检测 + 几何特征匹配 识别经典 K 线形态
    """

    PRICE_TOLERANCE = 0.03  # 价格相似度容差 3%
    MIN_PATTERN_BARS = 10   # 形态最少需要的 K 线数
    SWING_WINDOW = 5        # 拐点检测窗口

    def detect(self, df: pd.DataFrame) -> PatternDetectionReport:
        """
        对 DataFrame 执行完整的形态检测

        Args:
            df: 包含 OHLCV + MA 数据的 DataFrame，至少 60 行

        Returns:
            PatternDetectionReport
        """
        if len(df) < 30:
            return PatternDetectionReport(
                swing_highs=[], swing_lows=[], crossovers=[],
                patterns=[PatternResult('none', 0, '数据不足（少于30根K线），无法进行形态检测')],
                summary='数据不足，无法检测形态'
            )

        dates = self._get_dates(df)
        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values

        swing_highs = self._find_swing_points(highs, dates, 'high')
        swing_lows = self._find_swing_points(lows, dates, 'low')
        crossovers = self._detect_crossovers(df, dates)
        patterns: List[PatternResult] = []

        p = self._detect_double_top(swing_highs, swing_lows, closes, dates)
        if p:
            patterns.append(p)

        p = self._detect_double_bottom(swing_lows, swing_highs, closes, dates)
        if p:
            patterns.append(p)

        p = self._detect_head_shoulders_top(swing_highs, swing_lows, closes, dates)
        if p:
            patterns.append(p)

        p = self._detect_head_shoulders_bottom(swing_lows, swing_highs, closes, dates)
        if p:
            patterns.append(p)

        p = self._detect_triangle(swing_highs, swing_lows, closes, dates)
        if p:
            patterns.append(p)

        p = self._detect_channel(swing_highs, swing_lows, closes, dates)
        if p:
            patterns.append(p)

        p = self._detect_wedge(swing_highs, swing_lows, closes, dates)
        if p:
            patterns.append(p)

        p = self._detect_flag(df, swing_highs, swing_lows, closes, dates)
        if p:
            patterns.append(p)

        if not patterns:
            patterns.append(PatternResult('none', 0, '未检测到明显的经典形态'))

        patterns.sort(key=lambda x: x.confidence, reverse=True)

        summary = self._build_summary(patterns, crossovers, swing_highs, swing_lows, closes)
        return PatternDetectionReport(
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            crossovers=crossovers,
            patterns=patterns,
            summary=summary,
        )

    # ============ Swing Point Detection ============

    def _find_swing_points(self, prices: np.ndarray, dates: list, point_type: str) -> List[SwingPoint]:
        """使用滑动窗口检测局部极值拐点"""
        points = []
        w = self.SWING_WINDOW
        for i in range(w, len(prices) - w):
            window = prices[i - w: i + w + 1]
            if point_type == 'high' and prices[i] == window.max():
                if prices[i] > prices[i - 1] and prices[i] > prices[i + 1]:
                    points.append(SwingPoint(i, dates[i], float(prices[i]), 'high'))
            elif point_type == 'low' and prices[i] == window.min():
                if prices[i] < prices[i - 1] and prices[i] < prices[i + 1]:
                    points.append(SwingPoint(i, dates[i], float(prices[i]), 'low'))

        return self._deduplicate_swings(points)

    def _deduplicate_swings(self, points: List[SwingPoint], min_gap: int = 3) -> List[SwingPoint]:
        """去除过于密集的拐点，保留同方向中最极端的"""
        if not points:
            return []
        result = [points[0]]
        for p in points[1:]:
            if p.index - result[-1].index < min_gap:
                if p.type == 'high' and p.price > result[-1].price:
                    result[-1] = p
                elif p.type == 'low' and p.price < result[-1].price:
                    result[-1] = p
            else:
                result.append(p)
        return result

    # ============ MA Crossover Detection ============

    def _detect_crossovers(self, df: pd.DataFrame, dates: list) -> List[CrossoverSignal]:
        """检测均线交叉（金叉/死叉）"""
        signals = []
        pairs = [('MA5', 'MA20'), ('MA5', 'MA60'), ('MA20', 'MA60')]

        for fast, slow in pairs:
            if fast not in df.columns or slow not in df.columns:
                continue
            fast_vals = df[fast].values
            slow_vals = df[slow].values
            closes = df['Close'].values

            lookback = min(30, len(df) - 1)
            for i in range(len(df) - lookback, len(df)):
                if i < 1 or np.isnan(fast_vals[i]) or np.isnan(slow_vals[i]):
                    continue
                if np.isnan(fast_vals[i - 1]) or np.isnan(slow_vals[i - 1]):
                    continue

                prev_diff = fast_vals[i - 1] - slow_vals[i - 1]
                curr_diff = fast_vals[i] - slow_vals[i]

                if prev_diff <= 0 < curr_diff:
                    signals.append(CrossoverSignal(
                        date=dates[i], cross_type='golden_cross',
                        fast_ma=fast, slow_ma=slow,
                        price_at_cross=float(closes[i])
                    ))
                elif prev_diff >= 0 > curr_diff:
                    signals.append(CrossoverSignal(
                        date=dates[i], cross_type='death_cross',
                        fast_ma=fast, slow_ma=slow,
                        price_at_cross=float(closes[i])
                    ))

        return signals

    # ============ Pattern Detection Algorithms ============

    def _prices_similar(self, p1: float, p2: float) -> bool:
        avg = (p1 + p2) / 2
        return abs(p1 - p2) / avg < self.PRICE_TOLERANCE if avg > 0 else True

    def _detect_double_top(self, highs: List[SwingPoint], lows: List[SwingPoint],
                           closes: np.ndarray, dates: list) -> Optional[PatternResult]:
        """双顶检测：两个近似等高的高点 + 中间有明显的回落"""
        if len(highs) < 2:
            return None

        for i in range(len(highs) - 1):
            h1, h2 = highs[i], highs[i + 1]
            if h2.index - h1.index < self.MIN_PATTERN_BARS:
                continue
            if not self._prices_similar(h1.price, h2.price):
                continue

            valley_lows = [l for l in lows if h1.index < l.index < h2.index]
            if not valley_lows:
                continue
            neckline = min(l.price for l in valley_lows)
            peak_avg = (h1.price + h2.price) / 2
            depth = (peak_avg - neckline) / peak_avg
            if depth < 0.02:
                continue

            current = float(closes[-1])
            span = h2.index - h1.index
            total_expected = int(span * 1.5)
            elapsed = len(closes) - 1 - h1.index
            comp = min(100, int(elapsed / total_expected * 100)) if total_expected > 0 else 50

            confidence = min(85, 50 + depth * 500)

            return PatternResult(
                pattern_type='double_top_bottom',
                confidence=round(confidence),
                description=(
                    f"**双顶形态**：高点1 = {h1.price:.2f}（{h1.date}），"
                    f"高点2 = {h2.price:.2f}（{h2.date}），"
                    f"颈线 ≈ {neckline:.2f}，两高点间距 {h2.index - h1.index} 根K线。"
                    f"当前价格 {current:.2f}，"
                    f"{'已跌破颈线' if current < neckline else '仍在颈线上方'}。"
                ),
                key_points=[
                    {'label': '高点1', 'price': h1.price, 'date': h1.date},
                    {'label': '高点2', 'price': h2.price, 'date': h2.date},
                    {'label': '颈线', 'price': neckline, 'date': ''},
                ],
                completion_rate=comp,
            )
        return None

    def _detect_double_bottom(self, lows: List[SwingPoint], highs: List[SwingPoint],
                              closes: np.ndarray, dates: list) -> Optional[PatternResult]:
        """双底检测：两个近似等低的低点 + 中间有明显的反弹"""
        if len(lows) < 2:
            return None

        for i in range(len(lows) - 1):
            l1, l2 = lows[i], lows[i + 1]
            if l2.index - l1.index < self.MIN_PATTERN_BARS:
                continue
            if not self._prices_similar(l1.price, l2.price):
                continue

            peak_highs = [h for h in highs if l1.index < h.index < l2.index]
            if not peak_highs:
                continue
            neckline = max(h.price for h in peak_highs)
            trough_avg = (l1.price + l2.price) / 2
            depth = (neckline - trough_avg) / trough_avg
            if depth < 0.02:
                continue

            current = float(closes[-1])
            span = l2.index - l1.index
            total_expected = int(span * 1.5)
            elapsed = len(closes) - 1 - l1.index
            comp = min(100, int(elapsed / total_expected * 100)) if total_expected > 0 else 50

            confidence = min(85, 50 + depth * 500)

            return PatternResult(
                pattern_type='double_top_bottom',
                confidence=round(confidence),
                description=(
                    f"**双底形态**：低点1 = {l1.price:.2f}（{l1.date}），"
                    f"低点2 = {l2.price:.2f}（{l2.date}），"
                    f"颈线 ≈ {neckline:.2f}，两低点间距 {l2.index - l1.index} 根K线。"
                    f"当前价格 {current:.2f}，"
                    f"{'已突破颈线' if current > neckline else '仍在颈线下方'}。"
                ),
                key_points=[
                    {'label': '低点1', 'price': l1.price, 'date': l1.date},
                    {'label': '低点2', 'price': l2.price, 'date': l2.date},
                    {'label': '颈线', 'price': neckline, 'date': ''},
                ],
                completion_rate=comp,
            )
        return None

    def _detect_head_shoulders_top(self, highs: List[SwingPoint], lows: List[SwingPoint],
                                   closes: np.ndarray, dates: list) -> Optional[PatternResult]:
        """头肩顶检测：左肩-头-右肩，头最高，两肩近似等高"""
        if len(highs) < 3:
            return None

        for i in range(len(highs) - 2):
            ls, head, rs = highs[i], highs[i + 1], highs[i + 2]
            if head.price <= ls.price or head.price <= rs.price:
                continue
            if not self._prices_similar(ls.price, rs.price):
                continue
            if rs.index - ls.index < self.MIN_PATTERN_BARS:
                continue

            left_troughs = [l for l in lows if ls.index < l.index < head.index]
            right_troughs = [l for l in lows if head.index < l.index < rs.index]
            if not left_troughs or not right_troughs:
                continue

            neckline = (min(l.price for l in left_troughs) + min(l.price for l in right_troughs)) / 2
            head_height = (head.price - neckline) / head.price
            if head_height < 0.03:
                continue

            current = float(closes[-1])
            elapsed = len(closes) - 1 - ls.index
            total_expected = int((rs.index - ls.index) * 1.5)
            comp = min(100, int(elapsed / total_expected * 100)) if total_expected > 0 else 60
            confidence = min(90, 55 + head_height * 400)

            return PatternResult(
                pattern_type='head_shoulders',
                confidence=round(confidence),
                description=(
                    f"**头肩顶形态**：左肩 = {ls.price:.2f}（{ls.date}），"
                    f"头部 = {head.price:.2f}（{head.date}），"
                    f"右肩 = {rs.price:.2f}（{rs.date}），"
                    f"颈线 ≈ {neckline:.2f}。"
                    f"当前价格 {current:.2f}，"
                    f"{'已跌破颈线' if current < neckline else '仍在颈线上方'}。"
                ),
                key_points=[
                    {'label': '左肩', 'price': ls.price, 'date': ls.date},
                    {'label': '头部', 'price': head.price, 'date': head.date},
                    {'label': '右肩', 'price': rs.price, 'date': rs.date},
                    {'label': '颈线', 'price': round(neckline, 2), 'date': ''},
                ],
                completion_rate=comp,
            )
        return None

    def _detect_head_shoulders_bottom(self, lows: List[SwingPoint], highs: List[SwingPoint],
                                      closes: np.ndarray, dates: list) -> Optional[PatternResult]:
        """头肩底检测：左肩-头-右肩（低点），头最低，两肩近似等低"""
        if len(lows) < 3:
            return None

        for i in range(len(lows) - 2):
            ls, head, rs = lows[i], lows[i + 1], lows[i + 2]
            if head.price >= ls.price or head.price >= rs.price:
                continue
            if not self._prices_similar(ls.price, rs.price):
                continue
            if rs.index - ls.index < self.MIN_PATTERN_BARS:
                continue

            left_peaks = [h for h in highs if ls.index < h.index < head.index]
            right_peaks = [h for h in highs if head.index < h.index < rs.index]
            if not left_peaks or not right_peaks:
                continue

            neckline = (max(h.price for h in left_peaks) + max(h.price for h in right_peaks)) / 2
            head_depth = (neckline - head.price) / head.price
            if head_depth < 0.03:
                continue

            current = float(closes[-1])
            elapsed = len(closes) - 1 - ls.index
            total_expected = int((rs.index - ls.index) * 1.5)
            comp = min(100, int(elapsed / total_expected * 100)) if total_expected > 0 else 60
            confidence = min(90, 55 + head_depth * 400)

            return PatternResult(
                pattern_type='head_shoulders',
                confidence=round(confidence),
                description=(
                    f"**头肩底形态**：左肩 = {ls.price:.2f}（{ls.date}），"
                    f"头部 = {head.price:.2f}（{head.date}），"
                    f"右肩 = {rs.price:.2f}（{rs.date}），"
                    f"颈线 ≈ {neckline:.2f}。"
                    f"当前价格 {current:.2f}，"
                    f"{'已突破颈线' if current > neckline else '仍在颈线下方'}。"
                ),
                key_points=[
                    {'label': '左肩', 'price': ls.price, 'date': ls.date},
                    {'label': '头部', 'price': head.price, 'date': head.date},
                    {'label': '右肩', 'price': rs.price, 'date': rs.date},
                    {'label': '颈线', 'price': round(neckline, 2), 'date': ''},
                ],
                completion_rate=comp,
            )
        return None

    def _detect_triangle(self, highs: List[SwingPoint], lows: List[SwingPoint],
                         closes: np.ndarray, dates: list) -> Optional[PatternResult]:
        """三角形检测：高点趋势线 + 低点趋势线的收敛/扩散"""
        recent_highs = [h for h in highs if h.index >= len(closes) - 60]
        recent_lows = [l for l in lows if l.index >= len(closes) - 60]

        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        high_slope = self._calc_slope(recent_highs)
        low_slope = self._calc_slope(recent_lows)

        if high_slope is None or low_slope is None:
            return None

        converging = high_slope < 0 and low_slope > 0
        ascending = abs(high_slope) < 0.001 and low_slope > 0
        descending = high_slope < 0 and abs(low_slope) < 0.001

        if not (converging or ascending or descending):
            return None

        if converging:
            tri_type = '对称三角形'
        elif ascending:
            tri_type = '上升三角形'
        else:
            tri_type = '下降三角形'

        upper_bound = max(h.price for h in recent_highs)
        lower_bound = min(l.price for l in recent_lows)
        current = float(closes[-1])
        range_pct = (upper_bound - lower_bound) / lower_bound
        if range_pct < 0.02:
            return None

        first_idx = min(recent_highs[0].index, recent_lows[0].index)
        span = len(closes) - 1 - first_idx
        comp = min(95, int(span / max(span + 5, 1) * 100))

        confidence = 50
        if len(recent_highs) >= 3 and len(recent_lows) >= 3:
            confidence = 75
        elif len(recent_highs) >= 2 and len(recent_lows) >= 2:
            confidence = 60

        return PatternResult(
            pattern_type='triangle',
            confidence=confidence,
            description=(
                f"**{tri_type}**：近60日内检测到 {len(recent_highs)} 个高点"
                f"（{'→'.join(f'{h.price:.2f}' for h in recent_highs[-3:])}）"
                f"和 {len(recent_lows)} 个低点"
                f"（{'→'.join(f'{l.price:.2f}' for l in recent_lows[-3:])}），"
                f"{'高点逐渐降低，低点逐渐抬高' if converging else '高点水平，低点抬高' if ascending else '高点降低，低点水平'}，"
                f"形态区间 {lower_bound:.2f}-{upper_bound:.2f}。"
                f"当前价格 {current:.2f}。"
            ),
            key_points=[
                {'label': '上边界', 'price': upper_bound, 'date': recent_highs[-1].date},
                {'label': '下边界', 'price': lower_bound, 'date': recent_lows[-1].date},
            ],
            completion_rate=comp,
        )

    def _detect_channel(self, highs: List[SwingPoint], lows: List[SwingPoint],
                        closes: np.ndarray, dates: list) -> Optional[PatternResult]:
        """通道检测：高点和低点趋势线近似平行"""
        recent_highs = [h for h in highs if h.index >= len(closes) - 60]
        recent_lows = [l for l in lows if l.index >= len(closes) - 60]

        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        high_slope = self._calc_slope(recent_highs)
        low_slope = self._calc_slope(recent_lows)

        if high_slope is None or low_slope is None:
            return None

        both_positive = high_slope > 0.001 and low_slope > 0.001
        both_negative = high_slope < -0.001 and low_slope < -0.001
        both_flat = abs(high_slope) <= 0.001 and abs(low_slope) <= 0.001

        if not (both_positive or both_negative or both_flat):
            return None

        slope_ratio = min(abs(high_slope), abs(low_slope)) / max(abs(high_slope), abs(low_slope)) if max(abs(high_slope), abs(low_slope)) > 0 else 1
        if slope_ratio < 0.4 and not both_flat:
            return None

        if both_positive:
            ch_type = '上升通道'
        elif both_negative:
            ch_type = '下降通道'
        else:
            ch_type = '水平通道'

        upper = max(h.price for h in recent_highs)
        lower = min(l.price for l in recent_lows)
        current = float(closes[-1])
        width = (upper - lower) / lower
        if width < 0.02:
            return None

        first_idx = min(recent_highs[0].index, recent_lows[0].index)
        span = len(closes) - 1 - first_idx

        confidence = 50
        if len(recent_highs) >= 3 and len(recent_lows) >= 3 and slope_ratio > 0.6:
            confidence = 70
        elif slope_ratio > 0.5:
            confidence = 55

        return PatternResult(
            pattern_type='channel',
            confidence=confidence,
            description=(
                f"**{ch_type}**：近 {span} 个交易日，"
                f"高点序列（{'→'.join(f'{h.price:.2f}' for h in recent_highs[-3:])}）"
                f"与低点序列（{'→'.join(f'{l.price:.2f}' for l in recent_lows[-3:])}）"
                f"{'同向上行' if both_positive else '同向下行' if both_negative else '水平运行'}，"
                f"通道宽度 {width * 100:.1f}%。"
                f"当前价格 {current:.2f}。"
            ),
            key_points=[
                {'label': '通道上轨', 'price': upper, 'date': recent_highs[-1].date},
                {'label': '通道下轨', 'price': lower, 'date': recent_lows[-1].date},
            ],
            completion_rate=min(90, int(span / max(span + 10, 1) * 100)),
        )

    def _detect_wedge(self, highs: List[SwingPoint], lows: List[SwingPoint],
                      closes: np.ndarray, dates: list) -> Optional[PatternResult]:
        """楔形检测：两条趋势线同向收敛"""
        recent_highs = [h for h in highs if h.index >= len(closes) - 60]
        recent_lows = [l for l in lows if l.index >= len(closes) - 60]

        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None

        high_slope = self._calc_slope(recent_highs)
        low_slope = self._calc_slope(recent_lows)

        if high_slope is None or low_slope is None:
            return None

        both_up = high_slope > 0.001 and low_slope > 0.001
        both_down = high_slope < -0.001 and low_slope < -0.001

        if not (both_up or both_down):
            return None

        converging = abs(high_slope) != abs(low_slope)
        if both_up:
            converging = high_slope < low_slope
        else:
            converging = abs(high_slope) < abs(low_slope)

        if not converging:
            return None

        wedge_type = '上升楔形' if both_up else '下降楔形'
        current = float(closes[-1])
        upper = max(h.price for h in recent_highs)
        lower = min(l.price for l in recent_lows)

        first_idx = min(recent_highs[0].index, recent_lows[0].index)
        span = len(closes) - 1 - first_idx

        return PatternResult(
            pattern_type='wedge',
            confidence=55,
            description=(
                f"**{wedge_type}**：高点和低点{'同步上移但上方空间收窄' if both_up else '同步下移但下方空间收窄'}，"
                f"高点序列（{'→'.join(f'{h.price:.2f}' for h in recent_highs[-3:])}），"
                f"低点序列（{'→'.join(f'{l.price:.2f}' for l in recent_lows[-3:])}）。"
                f"当前价格 {current:.2f}。"
            ),
            key_points=[
                {'label': '上边界', 'price': upper, 'date': recent_highs[-1].date},
                {'label': '下边界', 'price': lower, 'date': recent_lows[-1].date},
            ],
            completion_rate=min(85, int(span / max(span + 10, 1) * 100)),
        )

    def _detect_flag(self, df: pd.DataFrame, highs: List[SwingPoint], lows: List[SwingPoint],
                     closes: np.ndarray, dates: list) -> Optional[PatternResult]:
        """旗形检测：急涨/急跌后的窄幅整理"""
        if len(closes) < 30:
            return None

        recent_range = closes[-15:]
        prior_move = closes[-30:-15]

        prior_change = (prior_move[-1] - prior_move[0]) / prior_move[0]
        recent_volatility = (recent_range.max() - recent_range.min()) / recent_range.mean()

        if abs(prior_change) < 0.05:
            return None
        if recent_volatility > 0.06:
            return None

        if prior_change > 0:
            flag_type = '上升旗形'
            direction = '急涨'
        else:
            flag_type = '下降旗形'
            direction = '急跌'

        current = float(closes[-1])
        flag_high = float(recent_range.max())
        flag_low = float(recent_range.min())

        return PatternResult(
            pattern_type='flag',
            confidence=60,
            description=(
                f"**{flag_type}**：前15个交易日{direction} {abs(prior_change) * 100:.1f}%，"
                f"随后在 {flag_low:.2f}-{flag_high:.2f} 区间"
                f"（波幅 {recent_volatility * 100:.1f}%）进行窄幅整理。"
                f"当前价格 {current:.2f}。"
            ),
            key_points=[
                {'label': '旗形上沿', 'price': flag_high, 'date': ''},
                {'label': '旗形下沿', 'price': flag_low, 'date': ''},
            ],
            completion_rate=70,
        )

    # ============ Helpers ============

    def _calc_slope(self, points: List[SwingPoint]) -> Optional[float]:
        """计算拐点序列的归一化斜率（每根K线的价格变化率）"""
        if len(points) < 2:
            return None
        x = np.array([p.index for p in points], dtype=float)
        y = np.array([p.price for p in points], dtype=float)
        avg_price = y.mean()
        if avg_price == 0:
            return None
        dx = x[-1] - x[0]
        if dx == 0:
            return 0.0
        slope = (y[-1] - y[0]) / dx / avg_price
        return slope

    def _get_dates(self, df: pd.DataFrame) -> list:
        """从 DataFrame 提取日期字符串列表"""
        if 'Date' in df.columns:
            return [str(d)[:10] for d in df['Date'].values]
        if 'trade_date' in df.columns:
            return [str(d)[:10] for d in df['trade_date'].values]
        if df.index.name and 'date' in df.index.name.lower():
            return [str(d)[:10] for d in df.index]
        return [str(i) for i in range(len(df))]

    def _build_summary(self, patterns: List[PatternResult], crossovers: List[CrossoverSignal],
                       highs: List[SwingPoint], lows: List[SwingPoint],
                       closes: np.ndarray) -> str:
        """构建人类可读的形态检测摘要"""
        parts = []

        top_pattern = patterns[0] if patterns else None
        if top_pattern and top_pattern.pattern_type != 'none':
            parts.append(f"算法检测到主要形态：{top_pattern.description}")
            if len(patterns) > 1 and patterns[1].pattern_type != 'none':
                parts.append(f"次要形态：{patterns[1].description}")
        else:
            parts.append("算法未检测到明显的经典技术形态。")

        if crossovers:
            recent = crossovers[-3:]
            cross_lines = []
            for c in recent:
                label = '金叉' if c.cross_type == 'golden_cross' else '死叉'
                cross_lines.append(f"- {c.date}：{c.fast_ma}/{c.slow_ma} {label}（价格 {c.price_at_cross:.2f}）")
            parts.append("近期均线交叉信号：\n" + "\n".join(cross_lines))

        if highs:
            recent_highs = highs[-3:]
            parts.append(
                f"近期高点拐点：{'、'.join(f'{h.price:.2f}({h.date})' for h in recent_highs)}"
            )
        if lows:
            recent_lows = lows[-3:]
            parts.append(
                f"近期低点拐点：{'、'.join(f'{l.price:.2f}({l.date})' for l in recent_lows)}"
            )

        return "\n\n".join(parts)


pattern_detector = PatternDetector()
