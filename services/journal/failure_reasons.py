from typing import Dict, Optional

FAILURE_REASON_LABELS: Dict[str, str] = {
    "direction_wrong": "方向判断错误",
    "timing_wrong": "时机判断错误",
    "volume_unconfirmed": "价格到了但量能未确认",
    "reverse_path": "市场走了反向路径",
    "logic_broken": "关键逻辑被破坏",
    "other": "其他原因",
}

VALID_FAILURE_REASONS = set(FAILURE_REASON_LABELS.keys())


def normalize_failure_reason(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = str(value).strip()
    if normalized not in VALID_FAILURE_REASONS:
        return None
    return normalized


def failure_reason_label(value: Optional[str]) -> Optional[str]:
    normalized = normalize_failure_reason(value)
    if not normalized:
        return None
    return FAILURE_REASON_LABELS[normalized]
