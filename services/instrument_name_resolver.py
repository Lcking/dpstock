"""
Resolve display names for stocks, ETFs, and LOF funds.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Tuple

from utils.logger import get_logger

logger = get_logger()

_ETF_NAME_CACHE: Dict[str, str] = {}
_LOF_NAME_CACHE: Dict[str, str] = {}
_CACHE_LOADED_AT: Dict[str, float] = {}
_CACHE_TTL_SECONDS = 30 * 60
_CACHE_LOCK = threading.Lock()


def _normalize_code(stock_code: str) -> str:
    return str(stock_code or "").strip().upper().split(".")[0]


def _cache_valid(market_type: str) -> bool:
    loaded_at = _CACHE_LOADED_AT.get(market_type)
    if loaded_at is None:
        return False
    cache = _ETF_NAME_CACHE if market_type == "ETF" else _LOF_NAME_CACHE
    return bool(cache) and (time.monotonic() - loaded_at) < _CACHE_TTL_SECONDS


def _load_fund_name_cache(market_type: str) -> Dict[str, str]:
    market_type = market_type if market_type in {"ETF", "LOF"} else "ETF"
    with _CACHE_LOCK:
        if _cache_valid(market_type):
            return _ETF_NAME_CACHE if market_type == "ETF" else _LOF_NAME_CACHE

    try:
        import akshare as ak

        if market_type == "ETF":
            df = ak.fund_etf_spot_em()
        else:
            df = ak.fund_lof_spot_em()
        mapping = {
            _normalize_code(str(row.get("代码") or "")): str(row.get("名称") or "").strip()
            for _, row in df.iterrows()
            if row.get("代码") and row.get("名称")
        }
    except Exception as exc:
        logger.warning(f"[InstrumentNameResolver] failed to load {market_type} names: {exc}")
        with _CACHE_LOCK:
            return _ETF_NAME_CACHE if market_type == "ETF" else _LOF_NAME_CACHE

    with _CACHE_LOCK:
        if market_type == "ETF":
            _ETF_NAME_CACHE.clear()
            _ETF_NAME_CACHE.update(mapping)
        else:
            _LOF_NAME_CACHE.clear()
            _LOF_NAME_CACHE.update(mapping)
        _CACHE_LOADED_AT[market_type] = time.monotonic()
        return _ETF_NAME_CACHE if market_type == "ETF" else _LOF_NAME_CACHE


def lookup_fund_name(stock_code: str, market_type: str = "ETF") -> str:
    code = _normalize_code(stock_code)
    if not code:
        return ""
    market_type = market_type if market_type in {"ETF", "LOF"} else "ETF"
    cache = _load_fund_name_cache(market_type)
    return cache.get(code, "")


def resolve_display_name(
    stock_code: str,
    market_type: str = "A",
    stock_name: str = "",
    *,
    allow_network: bool = False,
) -> str:
    name = str(stock_name or "").strip()
    if name:
        return name

    market_type = str(market_type or "A").strip().upper() or "A"
    code = _normalize_code(stock_code)
    if not code:
        return ""

    if market_type in {"ETF", "LOF"}:
        fund_name = lookup_fund_name(code, market_type)
        if fund_name:
            return fund_name

    if market_type == "A" and allow_network:
        try:
            from services.stock_data_provider import StockDataProvider

            resolved = StockDataProvider().lookup_stock_name(code, allow_network=True)
            if resolved:
                return resolved
        except Exception as exc:
            logger.debug(f"[InstrumentNameResolver] A-share lookup failed for {code}: {exc}")

    return ""


def market_category_label(market_type: str) -> str:
    return {
        "ETF": "ETF",
        "LOF": "LOF",
        "HK": "港股",
        "US": "美股",
        "A": "股票",
    }.get(str(market_type or "A").upper(), "标的")


def fallback_display_name(stock_code: str, market_type: str = "A") -> str:
    code = _normalize_code(stock_code)
    label = market_category_label(market_type)
    return f"{label} {code}" if code else label


def enrich_article_record(article: Dict[str, object]) -> Dict[str, object]:
    enriched = dict(article)
    code = str(enriched.get("stock_code") or "")
    market_type = str(enriched.get("market_type") or "A")
    resolved = resolve_display_name(
        code,
        market_type=market_type,
        stock_name=str(enriched.get("stock_name") or ""),
        allow_network=True,
    )
    if resolved:
        enriched["stock_name"] = resolved
    return enriched


def resolve_stock_page_info(
    stock_code: str,
    *,
    stock_name: str = "",
    market_type: str = "A",
) -> Optional[Tuple[str, str, str]]:
    code = _normalize_code(stock_code)
    if not code:
        return None
    market_type = str(market_type or "A").strip().upper() or "A"
    name = resolve_display_name(
        code,
        market_type=market_type,
        stock_name=stock_name,
        allow_network=True,
    )
    if not name:
        name = fallback_display_name(code, market_type)
    return code, name, market_type
