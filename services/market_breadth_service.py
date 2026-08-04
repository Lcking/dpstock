"""
A-share market breadth / temperature for homepage.

优先用东财指数 ulist 的涨跌家数字段（毫秒级）+ 涨停/跌停池总数，
避免全市场翻页把 /api/market-overview 拖到一分钟。
全市场 spot 仅作失败回退。
"""
from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

import requests

from utils.logger import get_logger

logger = get_logger()


class MarketBreadthService:
    CACHE_TTL_SECONDS = 300
    INTRADAY_CACHE_TTL_SECONDS = 45

    # 主板涨跌停近似阈值；创业板/科创板用 19.5（仅全市场回退路径使用）
    LIMIT_MAIN = 9.5
    LIMIT_GROWTH = 19.5

    EM_HOSTS = (
        "push2.eastmoney.com",
        "82.push2.eastmoney.com",
        "push2delay.eastmoney.com",
    )
    EM_EX_HOSTS = (
        "push2ex.eastmoney.com",
        "push2delay.eastmoney.com",
    )

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
            fast = self._fetch_breadth_fast()
            if fast is not None:
                return self._finalize_payload(fast, auction, source="eastmoney_ulist")
        except Exception as exc:
            logger.warning(f"[MarketBreadth] fast path failed: {exc}")

        try:
            spot = self._fetch_breadth_from_spot()
            if spot is not None:
                return self._finalize_payload(spot, auction, source="spot")
        except Exception as exc:
            logger.warning(f"[MarketBreadth] spot fallback failed: {exc}")

        return empty

    def _finalize_payload(
        self, counts: Dict[str, int], auction: Dict[str, Any], source: str
    ) -> Dict[str, Any]:
        up = int(counts.get("up") or 0)
        down = int(counts.get("down") or 0)
        flat = int(counts.get("flat") or 0)
        limit_up = int(counts.get("limit_up") or 0)
        limit_down = int(counts.get("limit_down") or 0)
        total = up + down + flat
        if total <= 0:
            return {
                "status": "unavailable",
                "up": up,
                "down": down,
                "flat": flat,
                "limit_up": limit_up,
                "limit_down": limit_down,
                "total": 0,
                "up_ratio": None,
                "temperature": None,
                "temperature_label": "暂不可用",
                "auction": auction,
                "source": source,
                "updated_at": int(time.time()),
            }

        up_ratio = up / total
        temperature = round(up_ratio * 100, 1)
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
            "temperature_label": self._temperature_label(temperature, limit_up, limit_down),
            "auction": auction,
            "source": source,
            "updated_at": int(time.time()),
        }

    def _fetch_breadth_fast(self) -> Optional[Dict[str, int]]:
        """东财指数成分涨跌家数 + 涨停/跌停池总数，通常 <1s。"""
        up_down = self._fetch_index_up_down_flat()
        if up_down is None:
            return None
        up, down, flat = up_down
        limit_up, limit_down = self._fetch_limit_pool_counts()
        return {
            "up": up,
            "down": down,
            "flat": flat,
            "limit_up": limit_up,
            "limit_down": limit_down,
        }

    def _fetch_index_up_down_flat(self) -> Optional[Tuple[int, int, int]]:
        """上证 + 深证成指的 f104/f105/f106 之和 ≈ 沪深 A 股涨跌家数。"""
        session = requests.Session()
        session.trust_env = False
        params = {
            "fltt": 2,
            "invt": 2,
            "secids": "1.000001,0.399001",
            "fields": "f12,f14,f104,f105,f106",
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://quote.eastmoney.com/",
        }
        last_error: Optional[Exception] = None
        for host in self.EM_HOSTS:
            try:
                resp = session.get(
                    f"https://{host}/api/qt/ulist.np/get",
                    params=params,
                    headers=headers,
                    timeout=8,
                    verify=False,
                )
                resp.raise_for_status()
                diff = ((resp.json() or {}).get("data") or {}).get("diff") or []
                if len(diff) < 2:
                    continue
                up = down = flat = 0
                for row in diff:
                    up += int(row.get("f104") or 0)
                    down += int(row.get("f105") or 0)
                    flat += int(row.get("f106") or 0)
                if up + down + flat < 1000:
                    continue
                return up, down, flat
            except Exception as exc:
                last_error = exc
                continue
        if last_error is not None:
            logger.warning(f"[MarketBreadth] ulist failed: {last_error}")
        return None

    def _fetch_limit_pool_counts(self) -> Tuple[int, int]:
        """涨停池 / 跌停池总数（tc）。失败时返回 0,0，不拖垮温度条。"""
        trade_date = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
        session = requests.Session()
        session.trust_env = False
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/ztzq/",
        }
        limit_up = self._fetch_topic_pool_total(
            session, headers, "getTopicZTPool", trade_date, sort="fbt:asc"
        )
        limit_down = self._fetch_topic_pool_total(
            session, headers, "getTopicDTPool", trade_date, sort="fund:asc"
        )
        return limit_up, limit_down

    def _fetch_topic_pool_total(
        self,
        session: requests.Session,
        headers: Dict[str, str],
        path: str,
        trade_date: str,
        sort: str,
    ) -> int:
        params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": 0,
            "pagesize": 20,
            "sort": sort,
            "date": trade_date,
        }
        for host in self.EM_EX_HOSTS:
            try:
                resp = session.get(
                    f"https://{host}/{path}",
                    params=params,
                    headers=headers,
                    timeout=6,
                    verify=False,
                )
                resp.raise_for_status()
                payload = resp.json() or {}
                if payload.get("rc") not in (0, "0", None):
                    continue
                data = payload.get("data") or {}
                total = data.get("tc")
                if total is None:
                    pool = data.get("pool") or []
                    return len(pool) if isinstance(pool, list) else 0
                return int(total)
            except Exception:
                continue
        return 0

    def _fetch_breadth_from_spot(self) -> Optional[Dict[str, int]]:
        """慢路径回退：全市场翻页聚合（可能数十秒，仅快路径失败时使用）。"""
        from services.risk_stock_collector import RiskStockCollector

        collector = RiskStockCollector()
        trade_date = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
        df = collector.fetch_spot_full_market(trade_date)
        if df is None or df.empty or "涨跌幅" not in df.columns:
            return None

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

        if up + down + flat <= 0:
            return None
        return {
            "up": up,
            "down": down,
            "flat": flat,
            "limit_up": limit_up,
            "limit_down": limit_down,
        }

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
