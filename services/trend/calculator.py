"""
Trend Calculator
趋势计算器 - 按 PRD Trend Spec T1-T6 实现

输出必须包含：direction、strength(0~100)、degraded、evidence[]
direction 与 strength 必须按本 Spec 计算，保证跨标的可比。
"""
from typing import Optional, List, Tuple
from .schemas import TrendInput, TrendResult


class TrendCalculator:
    """
    趋势计算器
    
    按 PRD v1.3 Trend Spec 实现:
    - T1: 输入字段
    - T2: 派生量 (dist200, slope200, ma_stack)
    - T3: direction 判定
    - T4: strength 计算 (0-100)
    - T5: evidence 生成 (2-5条)
    - T6: 降级处理
    """
    
    # 阈值常量
    DIST_STRONG_THRESHOLD = 0.02      # 强趋势距离阈值
    DIST_NEAR_THRESHOLD = 0.005       # 接近MA200阈值
    SLOPE_FLAT_THRESHOLD = 0.002      # 斜率走平阈值
    SLOPE_CALC_WINDOW = 20            # 斜率计算窗口
    
    def calculate(self, input_data: TrendInput) -> TrendResult:
        """
        计算趋势
        
        Args:
            input_data: TrendInput with price and MA data
            
        Returns:
            TrendResult with direction, strength, degraded, evidence
        """
        # T6: 降级检查 - 缺 MA200
        if input_data.ma200 is None:
            return TrendResult(
                direction="sideways",
                strength=0,
                degraded=True,
                evidence=["缺少MA200，无法判断趋势"]
            )
        
        # T2: 计算派生量
        dist200 = self._calc_dist200(input_data.close, input_data.ma200)
        slope200, slope_degraded = self._calc_slope200(input_data)
        ma_stack, stack_lite = self._calc_ma_stack(input_data)
        
        # T3: 判定 direction
        direction = self._determine_direction(dist200, slope200, ma_stack)
        
        # T4: 计算 strength
        strength = self._calc_strength(dist200, slope200, ma_stack, stack_lite)
        
        # T5: 生成 evidence
        evidence = self._generate_evidence(
            input_data, dist200, slope200, ma_stack, slope_degraded
        )
        
        # 降级标记
        degraded = slope_degraded or stack_lite
        
        return TrendResult(
            direction=direction,
            strength=strength,
            degraded=degraded,
            evidence=evidence
        )
    
    def _calc_dist200(self, close: float, ma200: float) -> float:
        """T2: dist200 = (close - ma200) / ma200"""
        if ma200 == 0:
            return 0.0
        return (close - ma200) / ma200
    
    def _calc_slope200(self, input_data: TrendInput) -> Tuple[float, bool]:
        """
        T2: slope200 = (ma200 - ma200_prev20) / ma200_prev20
        返回 (slope, degraded)
        """
        ma200 = input_data.ma200
        
        # 优先使用 prev20，备用 prev5
        ma200_prev = input_data.ma200_prev20
        if ma200_prev is None:
            ma200_prev = input_data.ma200_prev5
        
        if ma200_prev is None or ma200_prev == 0 or ma200 is None:
            return 0.0, True  # 降级
        
        slope = (ma200 - ma200_prev) / ma200_prev
        return slope, False
    
    def _calc_ma_stack(self, input_data: TrendInput) -> Tuple[str, bool]:
        """
        T2: 计算均线排列
        返回 (stack_type, is_lite)
        """
        ma5 = input_data.ma5
        ma20 = input_data.ma20
        ma60 = input_data.ma60
        
        # 完整排列判断
        if ma5 is not None and ma20 is not None and ma60 is not None:
            if ma5 > ma20 > ma60:
                return "BULL_STACK", False
            elif ma5 < ma20 < ma60:
                return "BEAR_STACK", False
            else:
                return "MIXED_STACK", False
        
        # LITE 模式：缺 ma5 或 ma60
        if ma20 is not None and ma60 is not None:
            if ma20 > ma60:
                return "BULL_STACK_LITE", True
            elif ma20 < ma60:
                return "BEAR_STACK_LITE", True
            else:
                return "MIXED_STACK", True
        
        # 均线严重缺失
        return "MIXED_STACK", True
    
    def _determine_direction(
        self, 
        dist200: float, 
        slope200: float, 
        ma_stack: str
    ) -> str:
        """
        T3: direction 判定
        
        1. 若 dist200>=+0.02 且 slope200>=0 → up
        2. 若 dist200<=-0.02 且 slope200<=0 → down
        3. 否则用 ma_stack + dist200 辅助判断
        """
        # 强趋势条件
        if dist200 >= self.DIST_STRONG_THRESHOLD and slope200 >= 0:
            return "up"
        if dist200 <= -self.DIST_STRONG_THRESHOLD and slope200 <= 0:
            return "down"
        
        # 辅助条件：用 ma_stack + dist200
        if ma_stack in ("BULL_STACK", "BULL_STACK_LITE") and dist200 >= 0:
            return "up"
        if ma_stack in ("BEAR_STACK", "BEAR_STACK_LITE") and dist200 <= 0:
            return "down"
        
        # 默认震荡
        return "sideways"
    
    def _calc_strength(
        self,
        dist200: float,
        slope200: float,
        ma_stack: str,
        stack_lite: bool
    ) -> int:
        """
        T4: strength 计算 (0-100)
        
        S_pos = min(abs(dist200)/0.10, 1) * 50
        S_slope = min(abs(slope200)/0.05, 1) * 30
        S_stack = 20 (full) / 12 (lite) / 5 (mixed) / 0 (degraded)
        """
        # S_pos: 距离贡献 (最多50分)
        s_pos = min(abs(dist200) / 0.10, 1.0) * 50
        
        # S_slope: 斜率贡献 (最多30分)
        s_slope = min(abs(slope200) / 0.05, 1.0) * 30
        
        # S_stack: 排列贡献
        if ma_stack in ("BULL_STACK", "BEAR_STACK"):
            s_stack = 20
        elif ma_stack in ("BULL_STACK_LITE", "BEAR_STACK_LITE"):
            s_stack = 12
        elif stack_lite:
            s_stack = 0  # 严重降级
        else:
            s_stack = 5  # MIXED
        
        strength = round(s_pos + s_slope + s_stack)
        return max(0, min(100, strength))
    
    def _generate_evidence(
        self,
        input_data: TrendInput,
        dist200: float,
        slope200: float,
        ma_stack: str,
        slope_degraded: bool
    ) -> List[str]:
        """
        T5: evidence 生成 (2-5条)
        
        必须包含:
        1. 价格相对MA200 (高于/低于/接近)
        2. MA200斜率 (上行/下行/走平)
        3. 均线排列 (牛/熊/交织)
        """
        evidence = []
        
        # 1. 价格相对MA200
        dist_pct = abs(dist200) * 100
        if abs(dist200) < self.DIST_NEAR_THRESHOLD:
            evidence.append(f"价格接近MA200（{dist200*100:.2f}%）")
        elif dist200 > 0:
            evidence.append(f"价格高于MA200（+{dist_pct:.2f}%）")
        else:
            evidence.append(f"价格低于MA200（-{dist_pct:.2f}%）")
        
        # 2. MA200斜率
        if slope_degraded:
            evidence.append("MA200斜率不可用（数据不足）")
        else:
            slope_pct = slope200 * 100
            if abs(slope200) < self.SLOPE_FLAT_THRESHOLD:
                evidence.append(f"MA200斜率走平（{slope_pct:.2f}%/20日）")
            elif slope200 > 0:
                evidence.append(f"MA200斜率上行（+{slope_pct:.2f}%/20日）")
            else:
                evidence.append(f"MA200斜率下行（{slope_pct:.2f}%/20日）")
        
        # 3. 均线排列
        stack_desc = {
            "BULL_STACK": "均线排列：MA5>MA20>MA60（多头）",
            "BEAR_STACK": "均线排列：MA5<MA20<MA60（空头）",
            "BULL_STACK_LITE": "均线排列：MA20>MA60（偏多）",
            "BEAR_STACK_LITE": "均线排列：MA20<MA60（偏空）",
            "MIXED_STACK": "均线排列：交织状态"
        }
        evidence.append(stack_desc.get(ma_stack, "均线排列：数据不足"))
        
        return evidence


# 单例
trend_calculator = TrendCalculator()
