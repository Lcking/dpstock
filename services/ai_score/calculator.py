"""
AI Score Calculator (Spec v1.0)

Implements the fixed, engineering-oriented scoring rules described in:
AI 综合评分工程化规则 Spec v1.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from utils.logger import get_logger
from utils.validation import normalize_ts_code
from services.tushare.orchestrator import enhancement_orchestrator
from services.trend.calculator import TrendCalculator
from services.trend.schemas import TrendInput

from .models import (
    AiScore,
    AiScoreContribItem,
    AiScoreDimension,
    AiScoreOverall,
    AiScoreExplain,
)

logger = get_logger()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _clamp_int(x: float, lo: int = 0, hi: int = 100) -> int:
    return int(_clamp(round(x), lo, hi))


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _key_metrics_map(module_result: Any) -> Dict[str, Any]:
    """
    Enhancements modules are ModuleResult with key_metrics: [{key,value,...}]
    Convert to {key: value} for easy access.
    """
    try:
        if not module_result or not getattr(module_result, "key_metrics", None):
            return {}
        return {m.key: m.value for m in module_result.key_metrics if getattr(m, "key", None)}
    except Exception:
        return {}


def _ma_stack_from_latest(ma5: Optional[float], ma20: Optional[float], ma60: Optional[float]) -> str:
    if ma5 is not None and ma20 is not None and ma60 is not None:
        if ma5 > ma20 > ma60:
            return "BULL_STACK"
        if ma5 < ma20 < ma60:
            return "BEAR_STACK"
        return "MIXED_STACK"
    if ma20 is not None and ma60 is not None:
        if ma20 > ma60:
            return "BULL_STACK_LITE"
        if ma20 < ma60:
            return "BEAR_STACK_LITE"
        return "MIXED_STACK"
    return "MIXED_STACK"


def _dist200(close: Optional[float], ma200: Optional[float]) -> Optional[float]:
    if close is None or ma200 is None or ma200 == 0:
        return None
    return (close - ma200) / ma200


def _overall_label(score: int) -> str:
    if score >= 80:
        return "结构偏强"
    if score >= 65:
        return "中性偏强"
    if score >= 45:
        return "中性偏弱"
    return "结构偏弱"


@dataclass
class _DimResult:
    score: int
    available: bool
    degraded: bool
    evidence: List[str]
    contrib: List[AiScoreContribItem]


class AiScoreCalculator:
    """
    Single entry point to calculate AiScore from indicator dataframe + enhancements.
    """

    VERSION = "1.0.0"

    WEIGHTS = {
        "structure": 0.30,
        "relative": 0.25,
        "flow": 0.25,
        "risk": 0.20,
    }

    def calculate(
        self,
        df: pd.DataFrame,
        stock_code: str,
        market_type: str = "A",
        analysis_v1: Optional[Dict[str, Any]] = None,
    ) -> AiScore:
        latest = df.iloc[-1] if not df.empty else None
        close = _safe_float(latest.get("Close")) if latest is not None else None
        ma5 = _safe_float(latest.get("MA5")) if latest is not None else None
        ma20 = _safe_float(latest.get("MA20")) if latest is not None else None
        ma60 = _safe_float(latest.get("MA60")) if latest is not None else None
        ma200 = _safe_float(latest.get("MA200")) if latest is not None else None

        ma200_prev20 = None
        ma200_prev5 = None
        try:
            if len(df) >= 21:
                ma200_prev20 = _safe_float(df.iloc[-21].get("MA200"))
            if len(df) >= 6:
                ma200_prev5 = _safe_float(df.iloc[-6].get("MA200"))
        except Exception:
            pass

        # Trend spec
        trend_calc = TrendCalculator()
        trend = trend_calc.calculate(
            TrendInput(
                close=close or 0.0,
                ma5=ma5,
                ma20=ma20,
                ma60=ma60,
                ma200=ma200,
                ma200_prev20=ma200_prev20,
                ma200_prev5=ma200_prev5,
            )
        )
        dist200 = _dist200(close, ma200)
        ma_stack = _ma_stack_from_latest(ma5, ma20, ma60)

        # Enhancements (A-share only). Others: unavailable.
        enh = None
        rs_mod = None
        flow_mod = None
        events_mod = None
        if market_type == "A":
            try:
                ts_code = normalize_ts_code(stock_code)
                enh = enhancement_orchestrator.enhance(ts_code)
                rs_mod = enh.relative_strength
                flow_mod = enh.capital_flow
                events_mod = enh.events
            except Exception as e:
                logger.warning(f"[AiScore] Enhancement unavailable for {stock_code}: {e}")
                enh = None

        # Extract misread flags from analysis_v1 if available
        risk_flags: List[str] = []
        try:
            if analysis_v1 and analysis_v1.get("risk_of_misreading"):
                risk_flags = list(analysis_v1["risk_of_misreading"].get("risk_flags") or [])
        except Exception:
            risk_flags = []

        structure_dim = self._calc_structure(trend, dist200, ma_stack)
        relative_dim = self._calc_relative(rs_mod)
        flow_dim = self._calc_flow(flow_mod, latest)
        risk_dim = self._calc_risk(events_mod, risk_flags, df)

        dims = {
            "structure": structure_dim,
            "relative": relative_dim,
            "flow": flow_dim,
            "risk": risk_dim,
        }

        # overall score uses fixed weights even when unavailable (Spec 6.2)
        overall_score = 0.0
        for dim_id, dim in dims.items():
            overall_score += dim.score * self.WEIGHTS[dim_id]

        overall_score_i = _clamp_int(overall_score, 0, 100)

        unavailable_count = sum(1 for d in dims.values() if not d.available)
        overall_degraded = unavailable_count >= 2

        confidence = self._calc_confidence(
            available_dims=4 - unavailable_count,
            events_flag=self._get_events_flag(events_mod),
            misread_penalty=self._misread_penalty(risk_flags),
        )

        explain = AiScoreExplain(
            one_liner=self._one_liner(structure_dim, relative_dim, flow_dim, risk_dim),
            notes=["评分为结构摘要，非预测，非建议。"],
        )

        dimensions_out = [
            AiScoreDimension(
                id="structure",
                name="趋势与结构",
                score=structure_dim.score,
                weight=self.WEIGHTS["structure"],
                contrib=structure_dim.contrib,
                evidence=structure_dim.evidence[:2],
                available=structure_dim.available,
                degraded=structure_dim.degraded,
            ),
            AiScoreDimension(
                id="relative",
                name="相对强弱",
                score=relative_dim.score,
                weight=self.WEIGHTS["relative"],
                contrib=relative_dim.contrib,
                evidence=relative_dim.evidence[:2],
                available=relative_dim.available,
                degraded=relative_dim.degraded,
            ),
            AiScoreDimension(
                id="flow",
                name="量价与资金",
                score=flow_dim.score,
                weight=self.WEIGHTS["flow"],
                contrib=flow_dim.contrib,
                evidence=flow_dim.evidence[:2],
                available=flow_dim.available,
                degraded=flow_dim.degraded,
            ),
            AiScoreDimension(
                id="risk",
                name="风险与扰动",
                score=risk_dim.score,
                weight=self.WEIGHTS["risk"],
                contrib=risk_dim.contrib,
                evidence=risk_dim.evidence[:2],
                available=risk_dim.available,
                degraded=risk_dim.degraded,
            ),
        ]

        return AiScore(
            version=self.VERSION,
            overall=AiScoreOverall(
                score=overall_score_i,
                label=_overall_label(overall_score_i),
                confidence=float(confidence),
                degraded=overall_degraded,
            ),
            dimensions=dimensions_out,
            explain=explain,
        )

    # ---------- Dimension calcs ----------

    def _calc_structure(self, trend: Any, dist200: Optional[float], ma_stack: str) -> _DimResult:
        available = True
        degraded = bool(getattr(trend, "degraded", False))
        evidence = list(getattr(trend, "evidence", []) or [])

        # Base: trend.strength
        base = int(getattr(trend, "strength", 0) or 0)
        direction = getattr(trend, "direction", "sideways")

        dir_adj = 8 if direction == "up" else (-8 if direction == "down" else 0)
        stack_adj = 0
        if ma_stack == "BULL_STACK":
            stack_adj = 10
        elif ma_stack == "BEAR_STACK":
            stack_adj = -10
        elif ma_stack == "BULL_STACK_LITE":
            stack_adj = 6
        elif ma_stack == "BEAR_STACK_LITE":
            stack_adj = -6

        d200_adj = 0
        if dist200 is None:
            # still available as long as trend exists
            pass
        else:
            if abs(dist200) < 0.005:
                d200_adj = 5
            elif dist200 >= 0.02:
                d200_adj = 5
            elif dist200 <= -0.02:
                d200_adj = -5

        score = _clamp_int(base + dir_adj + stack_adj + d200_adj)

        contrib = [
            AiScoreContribItem(
                key="trend_strength",
                value=base,
                impact=round(base * self.WEIGHTS["structure"], 2),
                note="Trend strength×0.30",
            ),
        ]
        if dir_adj != 0:
            contrib.append(
                AiScoreContribItem(
                    key="direction",
                    value=direction,
                    impact=round(dir_adj * self.WEIGHTS["structure"], 2),
                    note="方向修正×0.30",
                )
            )
        if stack_adj != 0:
            contrib.append(
                AiScoreContribItem(
                    key="stack",
                    value=ma_stack,
                    impact=round(stack_adj * self.WEIGHTS["structure"], 2),
                    note="排列修正×0.30",
                )
            )
        if d200_adj != 0:
            contrib.append(
                AiScoreContribItem(
                    key="dist200",
                    value=round(dist200, 4) if dist200 is not None else None,
                    impact=round(d200_adj * self.WEIGHTS["structure"], 2),
                    note="MA200位置修正×0.30",
                )
            )

        # Ensure at least 2 evidence lines when possible
        if not evidence:
            evidence = []
        if dist200 is not None:
            evidence.append("价格接近MA200" if abs(dist200) < 0.005 else "价格偏离MA200")
        evidence.append(f"均线排列 {ma_stack}")

        return _DimResult(score=score, available=available, degraded=degraded, evidence=evidence[:5], contrib=contrib)

    def _calc_relative(self, rs_mod: Any) -> _DimResult:
        weight = self.WEIGHTS["relative"]

        if not rs_mod or not getattr(rs_mod, "available", False):
            contrib = [AiScoreContribItem(key="unavailable", value=None, impact=0.0, note="相对强弱不可用→50")]
            return _DimResult(
                score=50,
                available=False,
                degraded=True,
                evidence=["相对强弱数据不可用"],
                contrib=contrib,
            )

        km = _key_metrics_map(rs_mod)
        # prefer spec name; fall back to common key used in watchlist summaries
        excess_20d = _safe_float(km.get("excess_20d") or km.get("excess_20d_vs_000300") or km.get("excess_20d_vs_hs300"))
        excess_5d = _safe_float(km.get("excess_5d") or km.get("excess_5d_vs_000300"))
        excess_60d = _safe_float(km.get("excess_60d") or km.get("excess_60d_vs_000300"))

        cap = 0.10
        x = _clamp(excess_20d or 0.0, -cap, cap)
        rs_score = round(50 + (x / cap) * 50)

        stability_adj = 0
        if excess_5d is not None and excess_20d is not None and excess_60d is not None:
            s5 = 1 if excess_5d > 0 else (-1 if excess_5d < 0 else 0)
            s20 = 1 if excess_20d > 0 else (-1 if excess_20d < 0 else 0)
            s60 = 1 if excess_60d > 0 else (-1 if excess_60d < 0 else 0)
            if s5 == s20 == s60 and s20 != 0:
                stability_adj = 5
            elif (s5, s20, s60).count(1) >= 1 and (s5, s20, s60).count(-1) >= 1:
                stability_adj = -5

        score = _clamp_int(rs_score + stability_adj)

        evidence = []
        if excess_20d is not None:
            evidence.append(f"excess_20d={excess_20d:+.2%}")
        if stability_adj != 0:
            evidence.append("强弱同向更稳定" if stability_adj > 0 else "强弱信号存在冲突")

        contrib = [
            AiScoreContribItem(
                key="excess_20d",
                value=excess_20d,
                impact=round(score * weight, 2),
                note="Relative×0.25",
            )
        ]
        if stability_adj != 0:
            contrib.append(
                AiScoreContribItem(
                    key="stability_adj",
                    value=stability_adj,
                    impact=round(stability_adj * weight, 2),
                    note="稳定性修正×0.25",
                )
            )

        return _DimResult(score=score, available=True, degraded=bool(getattr(rs_mod, "degraded", False)), evidence=evidence[:5], contrib=contrib)

    def _calc_flow(self, flow_mod: Any, latest_row: Any) -> _DimResult:
        weight = self.WEIGHTS["flow"]
        if not flow_mod or not getattr(flow_mod, "available", False):
            return _DimResult(
                score=50,
                available=False,
                degraded=True,
                evidence=["资金/量价数据不可用"],
                contrib=[AiScoreContribItem(key="unavailable", value=None, impact=0.0, note="Flow不可用→50")],
            )

        km = _key_metrics_map(flow_mod)
        label = str(km.get("label") or getattr(flow_mod, "summary", "") or "")
        # Some modules may put label as key metric under different names
        if not label and km.get("flow_label"):
            label = str(km.get("flow_label"))

        base = 50
        # Spec 4.2
        if "承接" in label:
            base = 70
        elif "分歧" in label:
            base = 40
        elif "中性" in label:
            base = 55
        elif "观望" in label or "缩量" in label:
            base = 50

        inflow_5d = _safe_float(km.get("net_inflow_5d") or km.get("net_inflow5d"))
        inflow_adj = 0
        if inflow_5d is not None:
            inflow_adj = 10 if inflow_5d > 0 else (-10 if inflow_5d < 0 else 0)

        vol_ratio = None
        try:
            if latest_row is not None:
                vol_ratio = _safe_float(latest_row.get("Volume_Ratio"))
        except Exception:
            vol_ratio = None

        vol_adj = 0
        if vol_ratio is not None and vol_ratio >= 1.2:
            if "承接" in label:
                vol_adj = 5
            elif "分歧" in label:
                vol_adj = -5

        score = _clamp_int(base + inflow_adj + vol_adj)

        evidence = []
        if label:
            evidence.append(f"capital_flow.label={label}")
        if inflow_5d is not None:
            evidence.append("近5日净流入为正" if inflow_5d > 0 else "近5日净流入为负")

        contrib = [
            AiScoreContribItem(key="flow_label", value=label, impact=round(base * weight, 2), note="Label基础分×0.25")
        ]
        if inflow_adj != 0:
            contrib.append(
                AiScoreContribItem(key="net_inflow_5d", value=inflow_5d, impact=round(inflow_adj * weight, 2), note="净流入方向修正×0.25")
            )
        if vol_adj != 0:
            contrib.append(
                AiScoreContribItem(key="vol_ratio", value=vol_ratio, impact=round(vol_adj * weight, 2), note="放量可信度修正×0.25")
            )

        return _DimResult(score=score, available=True, degraded=bool(getattr(flow_mod, "degraded", False)), evidence=evidence[:5], contrib=contrib)

    def _calc_risk(self, events_mod: Any, risk_flags: List[str], df: pd.DataFrame) -> _DimResult:
        weight = self.WEIGHTS["risk"]
        base = 70
        score = float(base)

        events_flag = self._get_events_flag(events_mod)
        event_penalty = 0
        if events_flag == "major":
            event_penalty = 30
        elif events_flag == "minor":
            event_penalty = 10
        elif events_flag == "none":
            event_penalty = 0
        else:
            event_penalty = 5  # unavailable

        misread_penalty = self._misread_penalty(risk_flags)

        vol_adj = 0
        vol_percentile = self._vol_percentile(df)
        if vol_percentile is not None:
            if vol_percentile >= 80:
                vol_adj = -15
            elif vol_percentile >= 60:
                vol_adj = -8
            elif vol_percentile < 40:
                vol_adj = +5

        score = _clamp_int(score + vol_adj - event_penalty - misread_penalty)

        evidence = []
        evidence.append(f"events.flag={events_flag}")
        if risk_flags:
            evidence.append(f"误读风险: {', '.join(risk_flags[:2])}")

        contrib = [
            AiScoreContribItem(key="base", value=base, impact=round(base * weight, 2), note="起始分×0.20")
        ]
        if vol_adj != 0:
            contrib.append(AiScoreContribItem(key="vol_adj", value=vol_percentile, impact=round(vol_adj * weight, 2), note="波动分位修正×0.20"))
        if event_penalty != 0:
            contrib.append(AiScoreContribItem(key="event_penalty", value=events_flag, impact=round(-event_penalty * weight, 2), note="事件扣分×0.20"))
        if misread_penalty != 0:
            contrib.append(AiScoreContribItem(key="misread_penalty", value=misread_penalty, impact=round(-misread_penalty * weight, 2), note="误读风险扣分×0.20"))

        return _DimResult(
            score=score,
            available=True,  # spec says events unavailable still can compute
            degraded=False if events_flag in ("none", "minor", "major") else True,
            evidence=evidence[:5],
            contrib=contrib,
        )

    # ---------- Helpers ----------

    def _get_events_flag(self, events_mod: Any) -> str:
        if not events_mod or not getattr(events_mod, "available", False):
            return "unavailable"
        km = _key_metrics_map(events_mod)
        flag = km.get("flag")
        if flag:
            return str(flag)
        # fall back: search in summary
        summary = str(getattr(events_mod, "summary", "") or "")
        if "重大" in summary:
            return "major"
        if "轻微" in summary or "小" in summary:
            return "minor"
        if "无" in summary:
            return "none"
        return "unavailable"

    def _misread_penalty(self, risk_flags: List[str]) -> int:
        penalty = 0
        for f in (risk_flags or []):
            s = str(f)
            if ("均线" in s and ("重合" in s or "粘合" in s)) or "均线重合" in s:
                penalty += 8
            elif "背离" in s:
                penalty += 8
            elif "钝化" in s:
                penalty += 6
            elif "关键位" in s and ("不确定" in s or "接近" in s):
                penalty += 6
            else:
                penalty += 4
            if penalty >= 20:
                return 20
        return min(penalty, 20)

    def _vol_percentile(self, df: pd.DataFrame) -> Optional[float]:
        try:
            if df is None or df.empty or "Volatility" not in df.columns:
                return None
            recent = df.tail(90)
            cur = float(recent.iloc[-1]["Volatility"])
            series = recent["Volatility"].dropna()
            if len(series) < 5:
                return None
            # Prefer scipy if installed (it is already used elsewhere)
            try:
                import scipy.stats as stats  # type: ignore
                return float(stats.percentileofscore(series, cur))
            except Exception:
                # Simple percentile fallback
                return float((series < cur).mean() * 100)
        except Exception:
            return None

    def _calc_confidence(self, available_dims: int, events_flag: str, misread_penalty: int) -> float:
        base = {4: 0.85, 3: 0.75, 2: 0.60, 1: 0.45}.get(available_dims, 0.35)
        if events_flag == "major" or misread_penalty > 15:
            base -= 0.05
        return float(_clamp(base, 0.35, 0.90))

    def _one_liner(self, structure: _DimResult, relative: _DimResult, flow: _DimResult, risk: _DimResult) -> str:
        # Keep it descriptive, non-predictive
        parts = []
        parts.append(f"结构分{structure.score}")
        parts.append(f"强弱分{relative.score}")
        parts.append(f"资金分{flow.score}")
        parts.append(f"风险分{risk.score}")
        return "，".join(parts) + "。"

