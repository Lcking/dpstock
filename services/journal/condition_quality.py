"""
Condition quality leaderboard for reviewed journal judgments.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.journal.evaluator import _parse_condition


def classify_condition_description(description: str) -> Dict[str, str]:
    parsed = _parse_condition(description or "")
    return classify_parsed_condition(parsed)


def classify_parsed_condition(parsed: Dict[str, Any]) -> Dict[str, str]:
    kind = parsed.get("kind") or "unknown"
    volume_rule = parsed.get("volume_rule") or {}
    volume_type = volume_rule.get("type")

    if kind == "breakout":
        if volume_type == "above_ma20":
            return {"key": "breakout_volume", "label": "突破+放量"}
        return {"key": "breakout", "label": "突破"}

    if kind == "breakdown":
        if volume_type == "above_ma20":
            return {"key": "breakdown_volume", "label": "跌破+放量"}
        return {"key": "breakdown", "label": "跌破"}

    if kind == "range":
        if volume_type == "within_ma20":
            return {"key": "range_shrink_volume", "label": "区间震荡+缩量"}
        if volume_type == "above_ma20":
            return {"key": "range_volume", "label": "区间震荡+放量"}
        return {"key": "range", "label": "区间震荡"}

    return {"key": "other", "label": "其他条件"}


def extract_selected_condition_description(
    constraints: Dict[str, Any],
    candidate: str,
) -> str:
    if not constraints:
        return ""

    selected = str(constraints.get("selected_candidate_description") or "").strip()
    if selected:
        return selected

    candidate_key = str(candidate or "").upper()
    candidates = constraints.get("candidates")
    if isinstance(candidates, dict):
        return str(candidates.get(candidate_key) or candidates.get(candidate) or "").strip()
    if isinstance(candidates, list):
        for item in candidates:
            if not isinstance(item, dict):
                continue
            option_id = str(item.get("option_id") or item.get("id") or "").upper()
            if option_id == candidate_key:
                return str(item.get("description") or "").strip()
    return ""


def build_condition_quality_leaderboard(
    reviewed_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}

    for item in reviewed_items:
        outcome = item.get("outcome")
        if outcome not in {"supported", "falsified", "uncertain"}:
            outcome = "uncertain"

        profile = classify_condition_description(item.get("condition_description") or "")
        bucket = buckets.setdefault(
            profile["key"],
            {
                "key": profile["key"],
                "label": profile["label"],
                "reviewed_count": 0,
                "supported_count": 0,
                "falsified_count": 0,
                "uncertain_count": 0,
                "support_rate": None,
            },
        )
        bucket["reviewed_count"] += 1
        bucket[f"{outcome}_count"] += 1

    leaderboard = sorted(
        buckets.values(),
        key=lambda row: (-row["reviewed_count"], row["label"]),
    )
    for row in leaderboard:
        if row["reviewed_count"] > 0:
            row["support_rate"] = round(
                row["supported_count"] / row["reviewed_count"] * 100,
                2,
            )
    return leaderboard
