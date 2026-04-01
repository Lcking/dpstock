import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import httpx
from services.tushare.client import tushare_client
from utils.logger import get_logger

logger = get_logger()


@dataclass(frozen=True)
class MarketIndexSpec:
    key: str
    name: str
    market: str
    symbol: str
    tushare_symbol: str | None = None
    yfinance_symbol: str | None = None


class MarketOverviewService:
    """轻量首页指数快照服务。"""

    CACHE_TTL_SECONDS = 300
    INTRADAY_CACHE_TTL_SECONDS = 30
    TREND_POINTS = 20
    JUMDATA_MINK_URL = "https://csjrgpsj.api.bdymkt.com/stock/hs/mink"

    INDEX_SPECS = [
        MarketIndexSpec(
            key="shanghai",
            name="上证指数",
            market="A",
            symbol="000001.SH",
            tushare_symbol="000001.SH",
            yfinance_symbol="000001.SS",
        ),
        MarketIndexSpec(
            key="csi300",
            name="沪深300",
            market="A",
            symbol="000300.SH",
            tushare_symbol="000300.SH",
            yfinance_symbol="000300.SS",
        ),
        MarketIndexSpec(key="hangseng", name="恒生指数", market="HK", symbol="^HSI", yfinance_symbol="^HSI"),
        MarketIndexSpec(key="nasdaq", name="纳斯达克", market="US", symbol="^IXIC", yfinance_symbol="^IXIC"),
    ]

    def __init__(self) -> None:
        self._cache: Dict[str, Any] | None = None
        self._cache_at = 0.0

    def get_overview(self) -> Dict[str, Any]:
        now = time.time()
        if self._cache and now - self._cache_at < self._cache_ttl_seconds():
            return self._cache

        items = [self._fetch_index(spec) for spec in self.INDEX_SPECS]
        payload = {
            "items": items,
            "updated_at": int(now),
        }
        self._cache = payload
        self._cache_at = now
        return payload

    def _cache_ttl_seconds(self) -> int:
        return self.INTRADAY_CACHE_TTL_SECONDS if self._is_a_share_trading_time() else self.CACHE_TTL_SECONDS

    def _is_a_share_trading_time(self) -> bool:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        if now.weekday() >= 5:
            return False

        current_time = now.time()
        morning_open = (current_time.hour, current_time.minute) >= (9, 30)
        morning_close = (current_time.hour, current_time.minute) < (11, 30)
        afternoon_open = (current_time.hour, current_time.minute) >= (13, 0)
        afternoon_close = (current_time.hour, current_time.minute) < (15, 0)
        return (morning_open and morning_close) or (afternoon_open and afternoon_close)

    def _fetch_index(self, spec: MarketIndexSpec) -> Dict[str, Any]:
        if spec.market == "A":
            a_share_item = self._fetch_a_share_index(spec)
            if a_share_item is not None:
                return a_share_item

        return self._fetch_index_from_yfinance(spec)

    # 东方财富 secid 映射
    _EASTMONEY_SECID_MAP: Dict[str, str] = {
        "000001.SH": "1.000001",
        "000300.SH": "1.000300",
    }

    def _fetch_a_share_index(self, spec: MarketIndexSpec) -> Dict[str, Any] | None:
        # 1. 实时价格：优先 JumData 分钟级，回退东方财富
        realtime = self._fetch_a_share_index_minute_context(spec)
        if realtime is None:
            realtime = self._fetch_eastmoney_realtime(spec)

        # 2. 历史趋势 + 前收盘（用于 JumData 模式的涨跌计算）
        daily_context = self._fetch_a_share_index_daily_context(spec)

        if realtime is not None and realtime.get("change") is not None:
            trend = realtime.get("trend") or []
            if not trend and daily_context:
                trend = [round(float(v), 2) for v in daily_context["closes"][-self.TREND_POINTS:]]
            return {
                "key": spec.key,
                "name": spec.name,
                "market": spec.market,
                "symbol": spec.symbol,
                "price": realtime["latest_close"],
                "change": realtime["change"],
                "change_percent": realtime["change_percent"],
                "trend": trend,
                "status": "ok",
            }

        if realtime is not None and daily_context is not None:
            previous_close = self._resolve_previous_close(
                daily_context["trade_dates"],
                daily_context["closes"],
                realtime.get("trade_date", ""),
            )
            if previous_close:
                latest_close = realtime["latest_close"]
                change = latest_close - previous_close
                change_percent = (change / previous_close * 100) if previous_close else 0.0
                trend = realtime.get("trend") or [round(float(v), 2) for v in daily_context["closes"][-self.TREND_POINTS:]]
                return {
                    "key": spec.key,
                    "name": spec.name,
                    "market": spec.market,
                    "symbol": spec.symbol,
                    "price": round(latest_close, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_percent, 2),
                    "trend": trend,
                    "status": "ok",
                }

        if daily_context is not None:
            closes = daily_context["closes"]
            previous_close, latest_close = closes[-2], closes[-1]
            change = latest_close - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0.0
            return {
                "key": spec.key,
                "name": spec.name,
                "market": spec.market,
                "symbol": spec.symbol,
                "price": round(latest_close, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "trend": [round(float(value), 2) for value in closes[-self.TREND_POINTS:]],
                "status": "ok",
            }

        return None

    # Sina Finance real-time index quote (no auth, no redirect issues)
    _SINA_INDEX_MAP: Dict[str, str] = {
        "000001.SH": "s_sh000001",
        "000300.SH": "s_sh000300",
    }

    def _fetch_eastmoney_realtime(self, spec: MarketIndexSpec) -> Dict[str, Any] | None:
        """从东方财富获取 A 股指数实时行情，回退新浪财经"""
        result = self._fetch_eastmoney_realtime_inner(spec)
        if result is not None:
            return result
        return self._fetch_sina_realtime(spec)

    def _fetch_sina_realtime(self, spec: MarketIndexSpec) -> Dict[str, Any] | None:
        """新浪财经实时指数（免费、稳定、无重定向问题）"""
        sina_code = self._SINA_INDEX_MAP.get(spec.tushare_symbol or "")
        if not sina_code:
            return None
        try:
            url = f"https://hq.sinajs.cn/list={sina_code}"
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn/",
            }
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                text = resp.text

            # Format: var hq_str_s_sh000001="上证指数,3941.52,23.66,0.60,..."
            parts = text.split('"')
            if len(parts) < 2:
                return None
            fields = parts[1].split(",")
            if len(fields) < 4:
                return None

            price = float(fields[1])
            change = float(fields[2])
            change_pct = float(fields[3])

            return {
                "latest_close": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
                "trade_date": datetime.now().strftime("%Y%m%d"),
                "trend": [],
            }
        except Exception as exc:
            logger.warning(f"[MarketOverview] sina realtime failed for {spec.name}: {exc}")
            return None

    def _fetch_eastmoney_realtime_inner(self, spec: MarketIndexSpec) -> Dict[str, Any] | None:
        """从东方财富获取 A 股指数实时行情（免费，无需 API Key）"""
        secid = self._EASTMONEY_SECID_MAP.get(spec.tushare_symbol or "")
        if not secid:
            return None

        try:
            url = "https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": secid,
                "fields": "f43,f44,f45,f46,f47,f58,f60,f169,f170",
                "fltt": "2",
            }
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://quote.eastmoney.com/",
            }
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                resp = client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                body = resp.json()

            item = body.get("data")
            if not item:
                return None

            price = item.get("f43")
            change = item.get("f169")
            change_pct = item.get("f170")

            if price is None or price == "-":
                return None

            return {
                "latest_close": round(float(price), 2),
                "change": round(float(change), 2) if change is not None else None,
                "change_percent": round(float(change_pct), 2) if change_pct is not None else None,
                "trade_date": datetime.now().strftime("%Y%m%d"),
                "trend": [],
            }
        except Exception as exc:
            logger.warning(f"[MarketOverview] eastmoney realtime failed for {spec.name}: {exc}")
            return None

    def _fetch_a_share_index_daily_context(self, spec: MarketIndexSpec) -> Dict[str, Any] | None:
        if not spec.tushare_symbol:
            return None

        try:
            tushare_client.ensure_initialized(log_missing_token=False)
            if not tushare_client.is_available:
                return None

            start_date = (datetime.now() - timedelta(days=45)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")
            history = tushare_client.get_index_daily(
                spec.tushare_symbol,
                start_date=start_date,
                end_date=end_date,
            )
            if history is None or history.empty or "close" not in history.columns:
                return None

            ordered = history.sort_values("trade_date")[["trade_date", "close"]].dropna(subset=["close"])
            trade_dates = ordered["trade_date"].astype(str).tolist()
            closes = [float(value) for value in ordered["close"].tolist()]
            if len(closes) < 2 or len(trade_dates) < 2:
                return None

            return {"trade_dates": trade_dates, "closes": closes}
        except Exception as exc:
            logger.warning(f"[MarketOverview] tushare fetch failed for {spec.name}: {exc}")
            return None

    def _fetch_a_share_index_minute_context(self, spec: MarketIndexSpec) -> Dict[str, Any] | None:
        if not spec.tushare_symbol:
            return None

        try:
            payload = self._post_jumdata_form(
                self.JUMDATA_MINK_URL,
                {
                    "code": spec.tushare_symbol,
                    "period": "1",
                    "pageSize": str(self.TREND_POINTS),
                },
            )
            if not payload or payload.get("code") != 200:
                return None

            raw_list = payload.get("data", {}).get("list") or []
            ordered = sorted(raw_list, key=lambda item: str(item.get("day", "")))
            trend: List[float] = []
            latest_trade_date = None

            for row in ordered:
                close_value = row.get("close")
                if close_value in (None, ""):
                    continue
                try:
                    trend.append(round(float(close_value), 2))
                    latest_trade_date = str(row.get("day", "")).split(" ", 1)[0]
                except (TypeError, ValueError):
                    continue

            if not trend or not latest_trade_date:
                return None

            return {
                "latest_close": trend[-1],
                "trade_date": latest_trade_date,
                "trend": trend[-self.TREND_POINTS :],
            }
        except Exception as exc:
            logger.warning(f"[MarketOverview] jumdata minute fetch failed for {spec.name}: {exc}")
            return None

    def _post_jumdata_form(self, url: str, data: Dict[str, str]) -> Dict[str, Any] | None:
        app_code = os.getenv("JUMDATA_APP_CODE", "").strip()
        if not app_code:
            return None

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Bce-Signature": f"AppCode/{app_code}",
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, data=data)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _resolve_previous_close(trade_dates: List[str], closes: List[float], current_trade_date: str) -> float | None:
        if len(closes) < 1 or len(trade_dates) < 1:
            return None

        current_day = current_trade_date.replace("-", "")
        latest_daily_date = trade_dates[-1]
        if latest_daily_date == current_day and len(closes) >= 2:
            return closes[-2]
        return closes[-1]

    def _fetch_index_from_yfinance(self, spec: MarketIndexSpec) -> Dict[str, Any]:
        try:
            import yfinance as yf

            yf_symbol = spec.yfinance_symbol or spec.symbol
            history = yf.Ticker(yf_symbol).history(period="5d", interval="1d")
            if history is None or history.empty or len(history) < 2:
                raise ValueError("insufficient index history")

            close_series = history["Close"].dropna().tail(self.TREND_POINTS)
            closes = close_series.tail(2).tolist()
            if len(closes) < 2:
                raise ValueError("insufficient close history")

            previous_close = float(closes[-2])
            latest_close = float(closes[-1])
            change = latest_close - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0.0

            return {
                "key": spec.key,
                "name": spec.name,
                "market": spec.market,
                "symbol": spec.symbol,
                "price": round(latest_close, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "trend": [round(float(value), 2) for value in close_series.tolist()],
                "status": "ok",
            }
        except Exception as exc:
            logger.warning(f"[MarketOverview] failed to fetch {spec.name}: {exc}")
            return {
                "key": spec.key,
                "name": spec.name,
                "market": spec.market,
                "symbol": spec.symbol,
                "price": None,
                "change": None,
                "change_percent": None,
                "trend": [],
                "status": "unavailable",
            }
