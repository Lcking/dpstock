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
_LOAD_FAILURE_UNTIL: Dict[str, float] = {}
_CACHE_TTL_SECONDS = 30 * 60
_FAILURE_COOLDOWN_SECONDS = 5 * 60
_CACHE_LOCK = threading.Lock()


def _normalize_code(stock_code: str) -> str:
    return str(stock_code or "").strip().upper().split(".")[0]


def infer_market_type(stock_code: str, declared_market: str = "A") -> str:
    declared = str(declared_market or "A").strip().upper() or "A"
    if declared in {"ETF", "LOF", "HK", "US"}:
        return declared

    code = _normalize_code(stock_code)
    if not code:
        return declared
    if code.isalpha() and len(code) <= 5:
        return "US"
    if code.isdigit() and len(code) == 5:
        return "HK"
    if code.isdigit() and len(code) == 6:
        if code.startswith("161"):
            return "LOF"
        if code.startswith(("159", "51", "56", "58")):
            return "ETF"
    return "A"


def is_placeholder_name(name: str, stock_code: str) -> bool:
    label = str(name or "").strip()
    code = _normalize_code(stock_code)
    if not label or not code:
        return not bool(label)
    if label.upper() == code:
        return True
    for prefix in ("ETF", "LOF", "股票", "港股", "美股"):
        if label.upper() == f"{prefix} {code}":
            return True
    return False


def _accept_name(name: str, stock_code: str) -> str:
    cleaned = str(name or "").strip()
    if cleaned and not is_placeholder_name(cleaned, stock_code):
        return cleaned
    return ""


def _to_tushare_ts_code(stock_code: str) -> str:
    code = _normalize_code(stock_code)
    if code.startswith("6") or code.startswith("5"):
        return f"{code}.SH"
    return f"{code}.SZ"


def _cache_valid(market_type: str) -> bool:
    loaded_at = _CACHE_LOADED_AT.get(market_type)
    if loaded_at is None:
        return False
    cache = _ETF_NAME_CACHE if market_type == "ETF" else _LOF_NAME_CACHE
    return bool(cache) and (time.monotonic() - loaded_at) < _CACHE_TTL_SECONDS


def _in_failure_cooldown(market_type: str) -> bool:
    until = _LOAD_FAILURE_UNTIL.get(market_type)
    return until is not None and time.monotonic() < until


def _mark_load_failure(market_type: str) -> None:
    _LOAD_FAILURE_UNTIL[market_type] = time.monotonic() + _FAILURE_COOLDOWN_SECONDS


def _fetch_fund_mapping(market_type: str) -> Dict[str, str]:
    import akshare as ak

    if market_type == "ETF":
        df = ak.fund_etf_spot_em()
    else:
        df = ak.fund_lof_spot_em()
    return {
        _normalize_code(str(row.get("代码") or "")): str(row.get("名称") or "").strip()
        for _, row in df.iterrows()
        if row.get("代码") and row.get("名称")
    }


def _load_fund_name_cache(market_type: str, *, force: bool = False) -> Dict[str, str]:
    market_type = market_type if market_type in {"ETF", "LOF"} else "ETF"
    with _CACHE_LOCK:
        if not force and _cache_valid(market_type):
            return _ETF_NAME_CACHE if market_type == "ETF" else _LOF_NAME_CACHE
        if not force and _in_failure_cooldown(market_type):
            return _ETF_NAME_CACHE if market_type == "ETF" else _LOF_NAME_CACHE

    mapping: Dict[str, str] = {}
    last_error: Optional[Exception] = None
    for attempt in range(3):
        try:
            mapping = _fetch_fund_mapping(market_type)
            if mapping:
                break
        except Exception as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))

    if not mapping:
        if last_error is not None:
            logger.warning(
                f"[InstrumentNameResolver] failed to load {market_type} names after retries: {last_error}"
            )
        _mark_load_failure(market_type)
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
        _LOAD_FAILURE_UNTIL.pop(market_type, None)
        return _ETF_NAME_CACHE if market_type == "ETF" else _LOF_NAME_CACHE


def preload_fund_name_caches(*, force: bool = False) -> None:
    """Load ETF/LOF name caches once (for batch jobs)."""
    _load_fund_name_cache("ETF", force=force)
    _load_fund_name_cache("LOF", force=force)


def lookup_fund_name(stock_code: str, market_type: str = "ETF") -> str:
    code = _normalize_code(stock_code)
    if not code:
        return ""
    market_type = market_type if market_type in {"ETF", "LOF"} else "ETF"
    cache = _load_fund_name_cache(market_type)
    hit = cache.get(code, "")
    if hit:
        return hit
    return _lookup_tushare_fund_name(code)


def _lookup_tushare_fund_name(stock_code: str) -> str:
    try:
        from services.tushare.client import tushare_client

        tushare_client.ensure_initialized(log_missing_token=False)
        if not tushare_client.is_available:
            return ""
        ts_code = _to_tushare_ts_code(stock_code)
        df = tushare_client.query(
            "fund_basic",
            ts_code=ts_code,
            fields="ts_code,name,fund_type,market",
        )
        if df is not None and not df.empty:
            name = str(df.iloc[0].get("name") or "").strip()
            return name
    except Exception as exc:
        logger.debug(f"[InstrumentNameResolver] tushare fund_basic failed for {stock_code}: {exc}")
    return ""


def _lookup_static_name(stock_code: str, market_type: str) -> str:
    code = _normalize_code(stock_code)
    if not code:
        return ""

    if market_type == "US":
        from services.us_stock_service_async import POPULAR_US_STOCKS

        for row in POPULAR_US_STOCKS:
            if str(row.get("symbol") or "").upper() == code:
                return str(row.get("name") or "").strip()

    if market_type == "HK":
        from services.search_snapshot_service import POPULAR_HK_STOCKS

        for hk_code, hk_name in POPULAR_HK_STOCKS:
            if _normalize_code(hk_code) == code:
                return hk_name

    if market_type == "A":
        try:
            from services.search_snapshot_service import SearchSnapshotService

            for row in SearchSnapshotService().search_a_shares(code, limit=1):
                if _normalize_code(str(row.get("symbol") or "")) == code:
                    name = str(row.get("name") or "").strip()
                    if name and name != code:
                        return name
        except Exception as exc:
            logger.debug(f"[InstrumentNameResolver] snapshot lookup failed for {code}: {exc}")

    return ""


def _lookup_tushare_stock_name(stock_code: str) -> str:
    try:
        from services.tushare.client import tushare_client

        tushare_client.ensure_initialized(log_missing_token=False)
        if not tushare_client.is_available:
            return ""
        df = tushare_client.get_stock_basic(_to_tushare_ts_code(stock_code))
        if df is not None and not df.empty:
            return str(df.iloc[0].get("name") or "").strip()
    except Exception as exc:
        logger.debug(f"[InstrumentNameResolver] tushare stock_basic failed for {stock_code}: {exc}")
    return ""


def resolve_display_name(
    stock_code: str,
    market_type: str = "A",
    stock_name: str = "",
    *,
    allow_network: bool = False,
) -> str:
    code = _normalize_code(stock_code)
    if not code:
        return ""

    existing = _accept_name(stock_name, code)
    if existing:
        return existing

    effective_market = infer_market_type(code, market_type)

    if effective_market in {"ETF", "LOF"}:
        fund_name = lookup_fund_name(code, effective_market)
        if fund_name:
            return fund_name

    static_name = _lookup_static_name(code, effective_market)
    if static_name:
        return static_name

    if effective_market == "A" and allow_network:
        resolved = _lookup_tushare_stock_name(code)
        if resolved:
            return resolved
        try:
            from services.stock_data_provider import StockDataProvider

            resolved = StockDataProvider().lookup_stock_name(code, allow_network=True)
            if resolved:
                return resolved
        except Exception as exc:
            logger.debug(f"[InstrumentNameResolver] A-share lookup failed for {code}: {exc}")

    if effective_market in {"ETF", "LOF"} and allow_network:
        return _lookup_tushare_fund_name(code)

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
    declared_market = str(enriched.get("market_type") or "A")
    effective_market = infer_market_type(code, declared_market)
    if effective_market != declared_market:
        enriched["market_type"] = effective_market

    current_name = str(enriched.get("stock_name") or "")
    if is_placeholder_name(current_name, code):
        current_name = ""

    resolved = resolve_display_name(
        code,
        market_type=effective_market,
        stock_name=current_name,
        allow_network=True,
    )
    if resolved:
        enriched["stock_name"] = resolved
    elif code:
        enriched["stock_name"] = fallback_display_name(code, effective_market)
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
    effective_market = infer_market_type(code, market_type)
    current_name = stock_name
    if is_placeholder_name(str(current_name or ""), code):
        current_name = ""
    name = resolve_display_name(
        code,
        market_type=effective_market,
        stock_name=str(current_name or ""),
        allow_network=True,
    )
    if not name:
        name = fallback_display_name(code, effective_market)
    return code, name, effective_market
