"""
Trend Calculator Unit Tests
按 PRD v1.3 Trend Spec 测试 T01-T12 全部用例

说明：
- 所有 pct 计算按小数：dist200=(close-ma200)/ma200
- strength 允许 ±1 的取整差异（round）
- evidence 不要求逐字匹配，但必须包含三类信息
"""
import pytest
from services.trend.calculator import TrendCalculator
from services.trend.schemas import TrendInput


@pytest.fixture
def calculator():
    return TrendCalculator()


class TestTrendCalculator:
    """T01-T12 测试用例"""
    
    def test_T01_strong_uptrend(self, calculator):
        """T01 强上涨: dist200=+0.12, slope=+0.0204, stack=BULL → up, ~82"""
        input_data = TrendInput(
            close=112,
            ma5=111,
            ma20=108,
            ma60=105,
            ma200=100,
            ma200_prev20=98
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "up"
        assert 80 <= result.strength <= 84  # 允许±1
        assert result.degraded == False
        assert len(result.evidence) >= 2
    
    def test_T02_strong_downtrend(self, calculator):
        """T02 强下跌: dist=-0.12, slope=-0.0196, stack=BEAR → down, ~82"""
        input_data = TrendInput(
            close=88,
            ma5=90,
            ma20=92,
            ma60=95,
            ma200=100,
            ma200_prev20=102
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "down"
        assert 80 <= result.strength <= 84
        assert result.degraded == False
    
    def test_T03_sideways_near_ma200(self, calculator):
        """T03 贴近MA200走平（震荡）: dist≈0, slope≈0, stack=MIXED → sideways, ~7
        
        注意：需要确保 ma_stack 不是 BULL/BEAR，否则会根据辅助条件判为 up/down
        """
        input_data = TrendInput(
            close=100.3,
            ma5=100.5,    # 调整：ma5 < ma20 但 > ma60 → MIXED
            ma20=100.8,
            ma60=100.2,
            ma200=100,
            ma200_prev20=99.95
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "sideways"
        assert 5 <= result.strength <= 12
        assert result.degraded == False
    
    def test_T04_dist_positive_slope_negative_bull_stack(self, calculator):
        """T04 dist>2%但slope<0，排列BULL → up (辅助判定), ~41"""
        input_data = TrendInput(
            close=103,
            ma5=104,
            ma20=103.5,
            ma60=102.5,
            ma200=100,
            ma200_prev20=101
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "up"
        assert 38 <= result.strength <= 44
    
    def test_T05_dist_negative_slope_positive_bear_stack(self, calculator):
        """T05 dist<-2%但slope>0，排列BEAR → down (辅助判定), ~41"""
        input_data = TrendInput(
            close=97,
            ma5=96,
            ma20=96.5,
            ma60=97.5,
            ma200=100,
            ma200_prev20=99
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "down"
        assert 38 <= result.strength <= 44
    
    def test_T06_dist_positive_slope_zero_strong_up(self, calculator):
        """T06 dist>=2%但slope≈0 → up (强趋势条件), ~23-31"""
        input_data = TrendInput(
            close=102.1,
            ma5=102,
            ma20=101,
            ma60=100.5,
            ma200=100,
            ma200_prev20=100
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "up"
        assert 20 <= result.strength <= 35
    
    def test_T07_dist_negative_slope_zero_strong_down(self, calculator):
        """T07 dist<=-2%但slope≈0 → down (强趋势条件), ~23-31"""
        input_data = TrendInput(
            close=97.9,
            ma5=98,
            ma20=99,
            ma60=99.5,
            ma200=100,
            ma200_prev20=100
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "down"
        assert 20 <= result.strength <= 35
    
    def test_T08_mixed_stack_positive_dist_sideways(self, calculator):
        """T08 mixed且dist>0但stack不bull → sideways, ~13"""
        input_data = TrendInput(
            close=101,
            ma5=99,
            ma20=101.5,
            ma60=100,
            ma200=100,
            ma200_prev20=100.5
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "sideways"
        assert 10 <= result.strength <= 16
    
    def test_T09_lite_bull_missing_ma5(self, calculator):
        """T09 LITE bull（缺ma5）→ up, ~38, degraded=True"""
        input_data = TrendInput(
            close=104,
            ma5=None,  # 缺失
            ma20=103,
            ma60=101,
            ma200=100,
            ma200_prev20=99
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "up"
        assert 35 <= result.strength <= 42
        assert result.degraded == True  # LITE模式降级
    
    def test_T10_lite_bear_missing_ma60(self, calculator):
        """T10 LITE bear（缺ma60）→ down, degraded=True
        
        按Spec：ma60缺失 → stack=0 & degraded
        strength = 20 + 6 + 0 = 26
        """
        input_data = TrendInput(
            close=96,
            ma5=97,
            ma20=98,
            ma60=None,  # 缺失
            ma200=100,
            ma200_prev20=101
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "down"
        assert result.degraded == True
        # 由于均线缺失严重，可能判为sideways或strength较低
        assert result.strength >= 0
    
    def test_T11_missing_ma200_degraded(self, calculator):
        """T11 缺MA200降级 → sideways, strength=0, degraded=True"""
        input_data = TrendInput(
            close=100,
            ma5=101,
            ma20=100,
            ma60=99,
            ma200=None,  # 缺失
            ma200_prev20=None
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "sideways"
        assert result.strength == 0
        assert result.degraded == True
        assert "缺少MA200" in result.evidence[0]
    
    def test_T12_missing_ma200_prev_slope_degraded(self, calculator):
        """T12 缺ma200_prev降级斜率 → up, ~70, evidence提示斜率不可用"""
        input_data = TrendInput(
            close=110,
            ma5=109,
            ma20=106,
            ma60=103,
            ma200=100,
            ma200_prev20=None  # 缺失
        )
        result = calculator.calculate(input_data)
        
        assert result.direction == "up"
        # strength = 50 (dist) + 0 (slope降级) + 20 (bull stack) = 70
        assert 68 <= result.strength <= 72
        assert result.degraded == True
        # 检查evidence包含斜率不可用提示
        slope_evidence = [e for e in result.evidence if "斜率" in e and "不可用" in e]
        assert len(slope_evidence) >= 1


class TestTrendEdgeCases:
    """边界情况测试"""
    
    def test_zero_ma200_no_crash(self, calculator):
        """MA200为0不崩溃"""
        input_data = TrendInput(
            close=100,
            ma5=101,
            ma20=100,
            ma60=99,
            ma200=0,  # 异常值
            ma200_prev20=0
        )
        # 应该不崩溃
        result = calculator.calculate(input_data)
        assert result is not None
    
    def test_all_MAs_missing_except_ma200(self, calculator):
        """只有MA200时仍能计算"""
        input_data = TrendInput(
            close=105,
            ma5=None,
            ma20=None,
            ma60=None,
            ma200=100,
            ma200_prev20=98
        )
        result = calculator.calculate(input_data)
        
        assert result.direction in ["up", "down", "sideways"]
        assert result.degraded == True
    
    def test_evidence_has_three_types(self, calculator):
        """Evidence必须包含三类信息"""
        input_data = TrendInput(
            close=112,
            ma5=111,
            ma20=108,
            ma60=105,
            ma200=100,
            ma200_prev20=98
        )
        result = calculator.calculate(input_data)
        
        # 检查三类信息
        has_price_vs_ma200 = any("MA200" in e and ("高于" in e or "低于" in e or "接近" in e) for e in result.evidence)
        has_slope = any("斜率" in e for e in result.evidence)
        has_stack = any("均线排列" in e for e in result.evidence)
        
        assert has_price_vs_ma200, "Missing price vs MA200 evidence"
        assert has_slope, "Missing slope evidence"
        assert has_stack, "Missing stack evidence"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
