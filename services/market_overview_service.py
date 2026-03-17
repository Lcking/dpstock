import time
from dataclasses import dataclass
from typing import Any, Dict, List

from utils.logger import get_logger

logger = get_logger()


@dataclass(frozen=True)
class MarketIndexSpec:
    key: str
    name: str
    market: str
    symbol: str


class MarketOverviewService:
    """轻量首页指数快照服务。"""

    CACHE_TTL_SECONDS = 300

    INDEX_SPECS = [
        MarketIndexSpec(key="shanghai", name="上证指数", market="A", symbol="000001.SS"),
        MarketIndexSpec(key="csi300", name="沪深300", market="A", symbol="000300.SS"),
        MarketIndexSpec(key="hangseng", name="恒生指数", market="HK", symbol="^HSI"),
        MarketIndexSpec(key="nasdaq", name="纳斯达克", market="US", symbol="^IXIC"),
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
        try:
            import yfinance as yf

            history = yf.Ticker(spec.symbol).history(period="5d", interval="1d")
            if history is None or history.empty or len(history) < 2:
                raise ValueError("insufficient index history")

            closes = history["Close"].dropna().tail(2).tolist()
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
                "status": "unavailable",
            }
