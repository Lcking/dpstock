"""
A-share market breadth / temperature for homepage.

复用风险池同款全市场快照（东财 → 新浪 → tushare），聚合涨跌家数与涨跌停，
附带轻量「竞价窗口」状态，供首页温度条使用。
"""
from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from utils.logger import get_logger

logger = get_logger()


class MarketBreadthService:
    CACHE_TTL_SECONDS = 300
    INTRADAY_CACHE_TTL_SECONDS = 45

    # 主板涨跌停近似阈值；创业板/科创板用 19.5
    LIMIT_MAIN = 9.5
    LIMIT_GROWTH = 19.5

    def __init__(self) -> None:
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_at = 0.0

    def get_breadth(self) -> Dict[str, Any]:
        now = time.time()
        ttl = (
            self.INTRADAY_CACHE_TTL_SECONDS
            if self._is_a_share_session()
            else self.CACHE_TTL_SECONDS
        )
        if self._cache and now - self._cache_at < ttl:
            return self._cache

        payload = self._build_breadth()
        self._cache = payload
        self._cache_at = now
        return payload

    def _build_breadth(self) -> Dict[str, Any]:
        auction = self._auction_window()
        empty = {
            "status": "unavailable",
            "up": 0,
            "down": 0,
            "flat": 0,
            "limit_up": 0,
            "limit_down": 0,
            "total": 0,
            "up_ratio": None,
            "temperature": None,
            "temperature_label": "暂不可用",
            "auction": auction,
            "source": None,
            "updated_at": int(time.time()),
        }
        try:
            from services.risk_stock_collector import RiskStockCollector

            collector = RiskStockCollector()
            trade_date = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
            df = collector._fetch_spot(trade_date)
            if df is None or df.empty or "涨跌幅" not in df.columns:
                return empty

            up = down = flat = limit_up = limit_down = 0
            for _, row in df.iterrows():
                code = str(row.get("代码") or "").strip().zfill(6)
                try:
                    pct = float(row.get("涨跌幅"))
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(pct):
                    continue
                if pct > 0:
                    up += 1
                elif pct < 0:
                    down += 1
                else:
                    flat += 1

                threshold = (
                    self.LIMIT_GROWTH
                    if code.startswith(("300", "301", "688", "689"))
                    else self.LIMIT_MAIN
                )
                if pct >= threshold:
                    limit_up += 1
                elif pct <= -threshold:
                    limit_down += 1

            total = up + down + flat
            if total <= 0:
                return empty

            up_ratio = up / total
            # 温度：上涨占比映射到 0–100，中性约 50
            temperature = round(up_ratio * 100, 1)
            label = self._temperature_label(temperature, limit_up, limit_down)

            return {
                "status": "ok",
                "up": up,
                "down": down,
                "flat": flat,
                "limit_up": limit_up,
                "limit_down": limit_down,
                "total": total,
                "up_ratio": round(up_ratio, 4),
                "temperature": temperature,
                "temperature_label": label,
                "auction": auction,
                "source": "spot",
                "updated_at": int(time.time()),
            }
        except Exception as exc:
            logger.warning(f"[MarketBreadth] build failed: {exc}")
            return empty

    @staticmethod
    def _temperature_label(temperature: float, limit_up: int, limit_down: int) -> str:
        if limit_up >= 80 and temperature >= 55:
            return "偏热"
        if limit_down >= 40 and temperature <= 45:
            return "偏冷"
        if temperature >= 60:
            return "偏强"
        if temperature <= 40:
            return "偏弱"
        return "中性"

    def _auction_window(self) -> Dict[str, Any]:
        """竞价窗口状态（不拉额外竞价盘口，只做时段感知）。"""
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        minutes = now.hour * 60 + now.minute
        # 集合竞价约 09:15–09:25，开盘缓冲到 09:30
        in_auction = now.weekday() < 5 and 9 * 60 + 15 <= minutes < 9 * 60 + 30
        after_open = now.weekday() < 5 and minutes >= 9 * 60 + 30
        if in_auction:
            phase = "auction"
            hint = "集合竞价进行中（09:15–09:25），关注高开低开与封单变化"
        elif after_open and minutes < 15 * 60:
            phase = "regular"
            hint = "已开盘；竞价简报仅作开盘参考"
        else:
            phase = "closed"
            hint = "非竞价时段"
        return {
            "phase": phase,
            "active": in_auction,
            "hint": hint,
            "window": "09:15–09:25",
        }

    @staticmethod
    def _is_a_share_session() -> bool:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        if now.weekday() >= 5:
            return False
        minutes = now.hour * 60 + now.minute
        return (9 * 60 + 15 <= minutes < 11 * 60 + 30) or (
            13 * 60 <= minutes < 15 * 60
        )


market_breadth_service = MarketBreadthService()
