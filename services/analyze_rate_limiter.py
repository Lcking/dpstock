"""
In-memory rate limiting for /api/analyze.

Buckets are keyed only by client IP. A new anonymous id must not reset them.
"""
from __future__ import annotations

import os
import time
from typing import Dict, List, Tuple

from utils.logger import get_logger

logger = get_logger()

_WINDOW_S = 60.0
_MAX_PER_WINDOW = int(os.getenv("ANALYZE_RATE_LIMIT_PER_MINUTE", "6"))
_DAILY_WINDOW_S = 24 * 60 * 60.0
_DAILY_MAX = int(os.getenv("ANALYZE_RATE_LIMIT_PER_DAY", "60"))

_window_buckets: Dict[str, List[float]] = {}
_daily_buckets: Dict[str, List[float]] = {}


def _prune(bucket: List[float], now: float, window_s: float) -> None:
    while bucket and now - bucket[0] > window_s:
        bucket.pop(0)


def _client_key(client_ip: str) -> str:
    safe_ip = str(client_ip or "unknown").strip() or "unknown"
    return f"ip:{safe_ip}"


def check_analyze_rate_limit(client_ip: str) -> Tuple[bool, str]:
    """
    Return (allowed, reason).
    reason is empty when allowed, otherwise a short machine-readable code.
    """
    key = _client_key(client_ip)
    now = time.monotonic()

    minute_bucket = _window_buckets.setdefault(key, [])
    _prune(minute_bucket, now, _WINDOW_S)
    if len(minute_bucket) >= _MAX_PER_WINDOW:
        logger.warning(f"[AnalyzeRateLimit] minute limit hit for {key}")
        return False, "rate_limit_minute"

    daily_bucket = _daily_buckets.setdefault(key, [])
    _prune(daily_bucket, now, _DAILY_WINDOW_S)
    if len(daily_bucket) >= _DAILY_MAX:
        logger.warning(f"[AnalyzeRateLimit] daily limit hit for {key}")
        return False, "rate_limit_daily"

    minute_bucket.append(now)
    daily_bucket.append(now)
    return True, ""


def reset_analyze_rate_limits() -> None:
    """Test helper."""
    _window_buckets.clear()
    _daily_buckets.clear()
