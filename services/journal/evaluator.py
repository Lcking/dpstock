import re
from typing import Any, Dict, Optional

import pandas as pd


def evaluate_journal_conditions(
    selected_candidate: str,
    candidate_descriptions: Dict[str, str],
    price_data: pd.DataFrame,
) -> Dict[str, Any]:
    """Evaluate the saved A/B/C judgment conditions against price and volume data."""
    selected_candidate = (selected_candidate or "").upper()
    candidate_results: Dict[str, Dict[str, Any]] = {}

    for option_id, description in candidate_descriptions.items():
        parsed = _parse_condition(description)
        candidate_results[option_id.upper()] = _evaluate_condition(parsed, price_data)

    selected_result = candidate_results.get(
        selected_candidate,
        _empty_result("missing_condition", "缺少所选候选条件原文，无法自动判卷"),
    )
    actual_path = _first_triggered_candidate(candidate_results)
    opposite = _opposite_candidate(selected_candidate)

    if selected_result["status"] == "triggered":
        outcome = "supported"
        actual_path = selected_candidate
        summary = f"{selected_candidate} 看涨条件已触发，判断得到市场支持。"
    elif opposite and candidate_results.get(opposite, {}).get("status") == "triggered":
        outcome = "falsified"
        actual_path = opposite
        summary = f"所选 {selected_candidate} 未触发，市场走出了 {opposite}，原判断被证伪。"
    elif selected_result["status"] == "partially_triggered":
        outcome = "uncertain"
        actual_path = None
        summary = _partial_summary(selected_candidate, selected_result)
    elif actual_path and actual_path != selected_candidate:
        outcome = "uncertain"
        summary = f"所选 {selected_candidate} 未触发，市场更接近 {actual_path} 路径。"
    else:
        outcome = "uncertain"
        actual_path = None
        summary = f"所选 {selected_candidate} 条件未触发，暂不能证明判断兑现。"

    return {
        "outcome": outcome,
        "actual_path": actual_path,
        "summary": summary,
        "selected_condition": selected_result,
        "candidate_results": candidate_results,
    }


def _parse_condition(description: str) -> Dict[str, Any]:
    text = description or ""
    if match := re.search(r"突破\s*([0-9]+(?:\.[0-9]+)?)", text):
        return {
            "kind": "breakout",
            "threshold": float(match.group(1)),
            "volume_rule": _parse_volume_rule(text),
            "raw": text,
        }
    if match := re.search(r"跌破\s*([0-9]+(?:\.[0-9]+)?)", text):
        return {
            "kind": "breakdown",
            "threshold": float(match.group(1)),
            "volume_rule": _parse_volume_rule(text),
            "raw": text,
        }
    if match := re.search(
        r"在\s*([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)\s*区间.*?(\d+)\s*个交易日",
        text,
    ):
        return {
            "kind": "range",
            "lower": float(match.group(1)),
            "upper": float(match.group(2)),
            "required_days": int(match.group(3)),
            "volume_rule": _parse_volume_rule(text),
            "raw": text,
        }
    return {"kind": "unknown", "raw": text}


def _parse_volume_rule(text: str) -> Optional[Dict[str, Any]]:
    if match := re.search(r"连续\s*(\d+)\s*日高于\s*20日均量\s*([0-9]+(?:\.[0-9]+)?)\s*倍", text):
        return {
            "type": "above_ma20",
            "consecutive_days": int(match.group(1)),
            "multiple": float(match.group(2)),
        }
    if match := re.search(r"放大至\s*20日均量的?\s*([0-9]+(?:\.[0-9]+)?)\s*倍以上", text):
        return {"type": "above_ma20", "consecutive_days": 1, "multiple": float(match.group(1))}
    if match := re.search(
        r"回落至\s*20日均量的?\s*([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)\s*倍",
        text,
    ):
        return {"type": "within_ma20", "lower": float(match.group(1)), "upper": float(match.group(2))}
    return None


def _evaluate_condition(condition: Dict[str, Any], price_data: pd.DataFrame) -> Dict[str, Any]:
    if condition.get("kind") == "unknown":
        return _empty_result("unknown_condition", "暂不支持解析该候选条件")
    if price_data is None or price_data.empty:
        return _empty_result("no_data", "缺少验证期行情数据")

    df = _normalize_price_frame(price_data)
    if condition["kind"] == "breakout":
        return _evaluate_breakout(condition, df)
    if condition["kind"] == "breakdown":
        return _evaluate_breakdown(condition, df)
    if condition["kind"] == "range":
        return _evaluate_range(condition, df)
    return _empty_result("unsupported_condition", "暂不支持该候选条件类型")


def _normalize_price_frame(price_data: pd.DataFrame) -> pd.DataFrame:
    df = price_data.copy()
    for column in ("Open", "High", "Low", "Close", "Volume"):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.dropna(subset=["Close"])


def _evaluate_breakout(condition: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    threshold = condition["threshold"]
    high = df["High"] if "High" in df.columns else df["Close"]
    price_trigger = bool((high >= threshold).any())
    volume_result = _evaluate_volume_rule(df, condition.get("volume_rule"))
    volume_trigger = volume_result["triggered"]
    status = _status_from_parts(price_trigger, volume_trigger)
    return {
        "status": status,
        "direction": "bullish",
        "price": {
            "type": "breakout",
            "threshold": threshold,
            "triggered": price_trigger,
            "max_price": _round_or_none(high.max()),
        },
        "volume": volume_result,
    }


def _evaluate_breakdown(condition: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    threshold = condition["threshold"]
    low = df["Low"] if "Low" in df.columns else df["Close"]
    price_trigger = bool((low <= threshold).any())
    volume_result = _evaluate_volume_rule(df, condition.get("volume_rule"))
    volume_trigger = volume_result["triggered"]
    status = _status_from_parts(price_trigger, volume_trigger)
    return {
        "status": status,
        "direction": "bearish",
        "price": {
            "type": "breakdown",
            "threshold": threshold,
            "triggered": price_trigger,
            "min_price": _round_or_none(low.min()),
        },
        "volume": volume_result,
    }


def _evaluate_range(condition: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    lower = condition["lower"]
    upper = condition["upper"]
    required_days = condition["required_days"]
    in_range = df["Close"].between(lower, upper)
    price_trigger = _has_consecutive_true(in_range, required_days)
    volume_result = _evaluate_volume_rule(df, condition.get("volume_rule"))
    volume_trigger = volume_result["triggered"]
    status = _status_from_parts(price_trigger, volume_trigger)
    return {
        "status": status,
        "direction": "neutral",
        "price": {
            "type": "range",
            "lower": lower,
            "upper": upper,
            "required_days": required_days,
            "triggered": price_trigger,
        },
        "volume": volume_result,
    }


def _evaluate_volume_rule(df: pd.DataFrame, rule: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not rule:
        return {"triggered": True, "reason": "未要求量能确认"}
    if "Volume" not in df.columns:
        return {"triggered": False, "reason": "缺少成交量数据"}

    volume = df["Volume"].dropna()
    ma20 = volume.rolling(window=20, min_periods=20).mean()
    ratio = volume / ma20

    if rule["type"] == "above_ma20":
        multiple = rule["multiple"]
        required_days = rule.get("consecutive_days", 1)
        triggered = _has_consecutive_true(ratio >= multiple, required_days)
        return {
            "triggered": triggered,
            "type": "above_ma20",
            "multiple": multiple,
            "required_consecutive_days": required_days,
            "max_ratio": _round_or_none(ratio.max()),
        }

    if rule["type"] == "within_ma20":
        lower = rule["lower"]
        upper = rule["upper"]
        triggered = bool(ratio.between(lower, upper).any())
        return {
            "triggered": triggered,
            "type": "within_ma20",
            "lower": lower,
            "upper": upper,
            "max_ratio": _round_or_none(ratio.max()),
            "min_ratio": _round_or_none(ratio.min()),
        }

    return {"triggered": False, "reason": "不支持的量能规则"}


def _has_consecutive_true(series: pd.Series, required_days: int) -> bool:
    streak = 0
    for value in series.fillna(False):
        streak = streak + 1 if bool(value) else 0
        if streak >= required_days:
            return True
    return False


def _status_from_parts(price_trigger: bool, volume_trigger: bool) -> str:
    if price_trigger and volume_trigger:
        return "triggered"
    if price_trigger or volume_trigger:
        return "partially_triggered"
    return "not_triggered"


def _first_triggered_candidate(candidate_results: Dict[str, Dict[str, Any]]) -> Optional[str]:
    for option_id in ("A", "B", "C"):
        if candidate_results.get(option_id, {}).get("status") == "triggered":
            return option_id
    return None


def _opposite_candidate(option_id: str) -> Optional[str]:
    return {"A": "C", "C": "A"}.get(option_id)


def _partial_summary(selected_candidate: str, selected_result: Dict[str, Any]) -> str:
    price_triggered = selected_result.get("price", {}).get("triggered")
    volume_triggered = selected_result.get("volume", {}).get("triggered")
    if price_triggered and not volume_triggered:
        return f"{selected_candidate} 价格已突破，但量能未确认，判断只能算部分兑现。"
    if volume_triggered and not price_triggered:
        return f"{selected_candidate} 量能满足，但价格条件未触发，判断尚未兑现。"
    return f"{selected_candidate} 条件部分满足，结果仍需人工复盘确认。"


def _empty_result(status: str, reason: str) -> Dict[str, Any]:
    return {"status": status, "reason": reason}


def _round_or_none(value: Any) -> Optional[float]:
    if pd.isna(value):
        return None
    return round(float(value), 2)
