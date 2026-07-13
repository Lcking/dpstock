"""
统一 A 股实时报价模块（新浪源）。

系统里所有“最新价格”最终只经过两个取数咽喉：
1. tushare_client.get_daily / get_index_daily（观察列表价格、趋势、相对强弱、资金流等）
2. StockDataProvider（分析、K线、信号扫描等）

收盘后日线 API 常滞后或返回未结算的当日 bar（bug 现场：002129 文章价 10.72 vs
实时收盘 10.66；/watchlist 价格滞后同因）。本模块提供：
- get_quote(): 带 TTL 缓存的新浪实时报价（避免观察列表多标的时打爆新浪）
- patch_tushare_daily(): 对 tushare daily 格式 DataFrame 补/校当日 bar

两个咽喉处统一调用，下游消费方无需感知。
可用环境变量 REALTIME_PRICE_PATCH_DISABLED=1 全局关闭。
"""
from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

import pandas as pd

from utils.logger import get_logger

logger = get_logger()

SHANGHAI = ZoneInfo("Asia/Shanghai")

# 报价缓存 TTL（秒）。观察列表一次会拉几十个标的，60s 内复用同一份报价。
QUOTE_CACHE_TTL_SECONDS = 60

_quote_cache: Dict[str, tuple[Optional[Dict[str, Any]], float]] = {}
_cache_lock = threading.Lock()


def realtime_patch_enabled() -> bool:
    return os.getenv("REALTIME_PRICE_PATCH_DISABLED", "").strip() not in ("1", "true", "yes")


def beijing_today_yyyymmdd() -> str:
    return datetime.now(SHANGHAI).strftime("%Y%m%d")


def to_sina_symbol(code: str) -> Optional[str]:
    """代码 → 新浪 hq 符号。支持 6 位裸代码与 ts_code（含指数）。

    002129 / 002129.SZ → sz002129；600519.SH → sh600519；000300.SH（指数）→ sh000300。
    北交所（.BJ）暂不支持，返回 None。
    """
    raw = str(code or "").strip().upper()
    if not raw:
        return None
    if "." in raw:
        symbol, _, suffix = raw.partition(".")
        symbol = symbol.strip()
        if not symbol.isdigit() or len(symbol) != 6:
            return None
        if suffix == "SH":
            return f"sh{symbol}"
        if suffix == "SZ":
            return f"sz{symbol}"
        return None  # .BJ 等
    if not raw.isdigit() or len(raw) != 6:
        return None
    # 裸代码启发式：5/6/9 开头为沪市（含 ETF/B股），其余深市
    if raw.startswith(("5", "6", "9")):
        return f"sh{raw}"
    return f"sz{raw}"


def _parse_sina_payload(text: str, code: str) -> Optional[Dict[str, Any]]:
    # var hq_str_sz002129="名称,开盘,昨收,现价,最高,最低,买一,卖一,成交量(股),成交额(元),...,日期,时间,..."
    parts = text.split('"')
    if len(parts) < 2:
        return None
    fields = parts[1].split(",")
    if len(fields) < 32:
        logger.warning(f"[RealtimeQuote] sina malformed {code}: fields={len(fields)}")
        return None
    try:
        open_px = float(fields[1])
        prev_close = float(fields[2])
        price = float(fields[3])
        high = float(fields[4])
        low = float(fields[5])
        volume = float(fields[8])
        amount = float(fields[9])
        trade_date = str(fields[30]).strip()
        trade_time = str(fields[31]).strip()
    except (TypeError, ValueError) as exc:
        logger.warning(f"[RealtimeQuote] sina parse failed {code}: {exc}")
        return None

    if price <= 0 or not trade_date:
        return None

    return {
        "open": open_px,
        "prev_close": prev_close,
        "price": price,
        "high": high,
        "low": low,
        "volume": volume,   # 股
        "amount": amount,   # 元
        "trade_date": trade_date,
        "trade_time": trade_time,
        "name": str(fields[0]).strip(),
    }


def _fetch_sina_quote(code: str) -> Optional[Dict[str, Any]]:
    import httpx

    symbol = to_sina_symbol(code)
    if not symbol:
        return None
    url = f"https://hq.sinajs.cn/list={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://finance.sina.com.cn/",
    }
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            text = resp.text
    except Exception as exc:
        logger.warning(f"[RealtimeQuote] sina fetch failed {code}: {exc}")
        return None
    return _parse_sina_payload(text, code)


def get_quote(code: str, ttl: int = QUOTE_CACHE_TTL_SECONDS) -> Optional[Dict[str, Any]]:
    """带 TTL 缓存的实时报价。失败结果也短暂缓存，避免反复打超时源。"""
    symbol = to_sina_symbol(code)
    if not symbol:
        return None

    import time

    now = time.monotonic()
    with _cache_lock:
        cached = _quote_cache.get(symbol)
        if cached is not None and now - cached[1] < ttl:
            return cached[0]

    quote = _fetch_sina_quote(code)
    with _cache_lock:
        _quote_cache[symbol] = (quote, now)
    return quote


def clear_quote_cache() -> None:
    with _cache_lock:
        _quote_cache.clear()


def should_patch_range(end_date: Optional[str]) -> bool:
    """请求区间不覆盖今天（历史回看/判卷）时禁止补当日 bar。"""
    if not realtime_patch_enabled():
        return False
    if not end_date:
        return True
    normalized = str(end_date).replace("-", "").strip()
    if len(normalized) != 8 or not normalized.isdigit():
        return True
    return normalized >= beijing_today_yyyymmdd()


def patch_tushare_daily(
    df: Optional[pd.DataFrame],
    ts_code: str,
    quote: Optional[Dict[str, Any]] = None,
    price_tol: float = 0.005,
) -> Optional[pd.DataFrame]:
    """
    用实时报价补/校 tushare daily 格式的 DataFrame。

    tushare 单位约定：vol=手，amount=千元；新浪：volume=股，amount=元。
    - 缺当日 bar：追加一行
    - 当日 bar 收盘价与实时不一致：覆盖
    行序不保证（tushare 默认倒序），消费方自行 sort_values('trade_date')。
    """
    if df is None or len(df) == 0 or "trade_date" not in df.columns:
        return df
    if quote is None:
        quote = get_quote(ts_code)
    if not quote:
        return df

    qdate = str(quote["trade_date"]).replace("-", "")
    if len(qdate) != 8:
        return df

    dates = df["trade_date"].astype(str).str.replace("-", "", regex=False)
    last_date = dates.max()
    if qdate < last_date:
        return df

    price = float(quote["price"])
    prev_close = float(quote.get("prev_close") or 0)
    open_px = float(quote.get("open") or price)
    high = float(quote.get("high") or price)
    low = float(quote.get("low") or price)
    vol_lots = float(quote.get("volume") or 0) / 100.0     # 股 → 手
    amount_k = float(quote.get("amount") or 0) / 1000.0    # 元 → 千元
    change = price - prev_close if prev_close else 0.0
    pct_chg = (change / prev_close * 100) if prev_close else 0.0

    out = df.copy()

    if qdate in set(dates):
        matches = out.index[dates == qdate]
        idx = matches[0]
        old_close = float(out.at[idx, "close"])
        if abs(old_close - price) <= price_tol:
            return out
        out.at[idx, "close"] = price
        if "open" in out.columns and open_px > 0:
            out.at[idx, "open"] = open_px
        if "high" in out.columns:
            out.at[idx, "high"] = max(float(out.at[idx, "high"]), high, price)
        if "low" in out.columns:
            existing_low = float(out.at[idx, "low"])
            out.at[idx, "low"] = min(existing_low, low if low > 0 else existing_low, price)
        if "vol" in out.columns and vol_lots > 0:
            out.at[idx, "vol"] = vol_lots
        if "amount" in out.columns and amount_k > 0:
            out.at[idx, "amount"] = amount_k
        if "pre_close" in out.columns and prev_close > 0:
            out.at[idx, "pre_close"] = prev_close
        if "change" in out.columns:
            out.at[idx, "change"] = round(change, 4)
        if "pct_chg" in out.columns:
            out.at[idx, "pct_chg"] = round(pct_chg, 4)
        logger.info(f"[RealtimeQuote] patch {ts_code} {qdate}: close {old_close:.2f} -> {price:.2f}")
        return out

    row: Dict[str, Any] = {col: None for col in out.columns}
    if "ts_code" in out.columns:
        row["ts_code"] = ts_code
    row["trade_date"] = qdate
    if "open" in out.columns:
        row["open"] = open_px
    if "high" in out.columns:
        row["high"] = max(high, open_px, price)
    if "low" in out.columns:
        row["low"] = min(low, open_px, price) if low > 0 else min(open_px, price)
    row["close"] = price
    if "pre_close" in out.columns:
        row["pre_close"] = prev_close if prev_close > 0 else None
    if "change" in out.columns:
        row["change"] = round(change, 4)
    if "pct_chg" in out.columns:
        row["pct_chg"] = round(pct_chg, 4)
    if "vol" in out.columns:
        row["vol"] = vol_lots
    if "amount" in out.columns:
        row["amount"] = amount_k

    out = pd.concat([out, pd.DataFrame([row])], ignore_index=True)
    logger.info(f"[RealtimeQuote] append {ts_code} {qdate}: close={price:.2f} (hist last={last_date})")
    return out
