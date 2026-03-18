import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List

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
    TREND_POINTS = 20

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
        if self._cache and now - self._cache_at < self.CACHE_TTL_SECONDS:
            return self._cache

        items = [self._fetch_index(spec) for spec in self.INDEX_SPECS]
        payload = {
            "items": items,
            "updated_at": int(now),
        }
        self._cache = payload
        self._cache_at = now
        return payload

    def _fetch_index(self, spec: MarketIndexSpec) -> Dict[str, Any]:
        if spec.market == "A":
            tushare_item = self._fetch_a_share_index_from_tushare(spec)
            if tushare_item is not None:
                return tushare_item

        return self._fetch_index_from_yfinance(spec)

    def _fetch_a_share_index_from_tushare(self, spec: MarketIndexSpec) -> Dict[str, Any] | None:
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

            ordered = history.sort_values("trade_date")
            close_series = ordered["close"].dropna().tail(self.TREND_POINTS)
            closes = [float(value) for value in close_series.tail(2).tolist()]
            if len(closes) < 2:
                return None

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
                "trend": [round(float(value), 2) for value in close_series.tolist()],
                "status": "ok",
            }
        except Exception as exc:
            logger.warning(f"[MarketOverview] tushare fetch failed for {spec.name}: {exc}")
            return None

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
