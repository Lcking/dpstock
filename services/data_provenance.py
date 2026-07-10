"""
Market data provenance helpers for analysis responses.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import pandas as pd


def resolve_data_source(market_type: str, price_df: Optional[pd.DataFrame] = None) -> str:
    if price_df is not None and bool(getattr(price_df, "attrs", {}).get("realtime_patched")):
        return "日线 + 新浪实时补丁"
    market = str(market_type or "A").upper()
    if market == "A":
        return "akshare / tushare"
    if market == "HK":
        return "雅虎财经"
    if market == "US":
        return "雅虎财经"
    if market == "ETF":
        return "akshare / 雅虎财经"
    return "公开市场数据"


def resolve_data_as_of(price_df: Optional[pd.DataFrame], fallback: Optional[datetime] = None) -> str:
    if price_df is not None and not price_df.empty:
        realtime_as_of = getattr(price_df, "attrs", {}).get("realtime_as_of")
        if realtime_as_of:
            return str(realtime_as_of)[:16]
        index = price_df.index[-1]
        if hasattr(index, "strftime"):
            return index.strftime("%Y-%m-%d %H:%M")
        text = str(index).strip()
        if text:
            return text[:16]
    if fallback is not None:
        return fallback.strftime("%Y-%m-%d %H:%M")
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def build_data_provenance(
    market_type: str,
    price_df: Optional[pd.DataFrame] = None,
    *,
    fallback: Optional[datetime] = None,
) -> dict[str, Any]:
    data_as_of = resolve_data_as_of(price_df, fallback=fallback)
    data_source = resolve_data_source(market_type, price_df)
    return {
        "data_as_of": data_as_of,
        "data_source": data_source,
        "data_provenance_label": f"数据截至 {data_as_of} · 来源：{data_source}",
    }
