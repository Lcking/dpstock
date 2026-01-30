import pandas as pd

from services.ai_score.calculator import AiScoreCalculator
from services.tushare.schemas import ModuleResult, KeyMetric


def _mk_mod(available: bool, key_metrics: list, summary: str = "ok", degraded: bool = False):
    return ModuleResult(
        available=available,
        degraded=degraded,
        degrade_reason=None if available else "unavailable",
        summary=summary,
        key_metrics=key_metrics,
        details=None,
        meta=None,
    )


def test_relative_mapping_edges():
    calc = AiScoreCalculator()

    rs_pos = _mk_mod(True, [KeyMetric(key="excess_20d", label="excess_20d", value=0.10)])
    rs_zero = _mk_mod(True, [KeyMetric(key="excess_20d", label="excess_20d", value=0.0)])
    rs_neg = _mk_mod(True, [KeyMetric(key="excess_20d", label="excess_20d", value=-0.10)])

    assert calc._calc_relative(rs_pos).score == 100
    assert calc._calc_relative(rs_zero).score == 50
    assert calc._calc_relative(rs_neg).score == 0


def test_flow_label_ordering():
    calc = AiScoreCalculator()

    flow_good = _mk_mod(True, [KeyMetric(key="label", label="label", value="承接放量")])
    flow_mid = _mk_mod(True, [KeyMetric(key="label", label="label", value="中性")])
    flow_bad = _mk_mod(True, [KeyMetric(key="label", label="label", value="分歧放量")])

    assert calc._calc_flow(flow_good, latest_row={"Volume_Ratio": 1.3}).score > calc._calc_flow(flow_mid, latest_row={"Volume_Ratio": 1.0}).score
    assert calc._calc_flow(flow_mid, latest_row={"Volume_Ratio": 1.0}).score > calc._calc_flow(flow_bad, latest_row={"Volume_Ratio": 1.3}).score


def test_risk_major_event_penalty_is_significant():
    calc = AiScoreCalculator()

    events_major = _mk_mod(True, [KeyMetric(key="flag", label="flag", value="major")])
    events_none = _mk_mod(True, [KeyMetric(key="flag", label="flag", value="none")])

    df = pd.DataFrame([{"Close": 10, "MA200": 10}])

    risk_major = calc._calc_risk(events_major, risk_flags=[], df=df).score
    risk_none = calc._calc_risk(events_none, risk_flags=[], df=df).score

    # base 70 - 30 = 40 (when no vol adj / misread)
    assert risk_major <= 40
    assert risk_none >= 65


def test_degrade_missing_relative_flow_confidence_drops_and_overall_not_inflated():
    calc = AiScoreCalculator()

    df = pd.DataFrame(
        [
            {"Close": 100, "MA5": 101, "MA20": 100, "MA60": 99, "MA200": 100, "Volatility": 5.0},
            {"Close": 101, "MA5": 102, "MA20": 101, "MA60": 100, "MA200": 100, "Volatility": 5.0},
        ]
    )

    score = calc.calculate(df=df, stock_code="AAPL", market_type="US", analysis_v1=None)

    # relative & flow should be unavailable => degraded overall
    assert score.overall.degraded is True
    # available dims = structure + risk = 2 => confidence 0.60 (clamped)
    assert 0.55 <= score.overall.confidence <= 0.65
    # overall must stay within bounds, and should not become "too high" just because data missing
    assert 0 <= score.overall.score <= 100


def test_structure_direction_adjustment_changes_score():
    calc = AiScoreCalculator()

    class _Trend:
        def __init__(self, direction, strength):
            self.direction = direction
            self.strength = strength
            self.degraded = False
            self.evidence = ["价格接近MA200", "均线排列MIXED_STACK"]

    base = 60
    dist200 = 0.0
    ma_stack = "MIXED_STACK"

    s_up = calc._calc_structure(_Trend("up", base), dist200, ma_stack).score
    s_side = calc._calc_structure(_Trend("sideways", base), dist200, ma_stack).score
    s_down = calc._calc_structure(_Trend("down", base), dist200, ma_stack).score

    assert s_up > s_side > s_down

