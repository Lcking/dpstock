"""
Collect daily risk stock candidates from public market data sources.

风险池口径：
- 连续涨停/跌停 ≥2 天（东财涨停池/跌停池）
- 当日涨幅 ≥5% 进 5%涨幅池，≥9% 进 9%涨幅池（全市场快照，回落自动移除）
- 创业板当日涨跌幅 ≥±15% 进创业板大波动池
- ST征兆：最近年报业绩预告首亏/续亏，或净资产为负（pb<0），且当前未戴帽
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from services.search_snapshot_service import SearchSnapshotService
from utils.logger import get_logger

logger = get_logger()

# ST征兆当日缓存：财务口径盘中不变，避免盘中每 15 分钟重复打 tushare
_st_omen_cache: Dict[str, List[Dict[str, Any]]] = {}
_st_omen_lock = threading.Lock()


def to_ts_code(code: str) -> str:
    normalized = str(code).strip().zfill(6)
    if normalized.startswith("6"):
        return f"{normalized}.SH"
    return f"{normalized}.SZ"


def is_chinext(code: str) -> bool:
    """创业板：300/301 开头。"""
    normalized = str(code).strip().zfill(6)
    return normalized.startswith(("300", "301"))


class RiskStockCollector:
    """Build risk-stock source rows from A-share snapshot, limit pools and spot quotes."""

    # 连板/连续跌停进入风险池的门槛（需求：连续 2 日即高风险）
    MIN_CONSECUTIVE_LIMIT_DAYS = 2
    GAIN_POOL_5 = 5.0
    GAIN_POOL_9 = 9.0
    CHINEXT_SWING = 15.0

    def __init__(self, snapshot_service: Optional[SearchSnapshotService] = None):
        self.snapshot_service = snapshot_service or SearchSnapshotService()

    def collect_rows(self, trade_date: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
        effective_date = trade_date or self._resolve_trade_date()
        rows_by_code: Dict[str, Dict[str, Any]] = {}

        def merge(row: Dict[str, Any]) -> None:
            existing = rows_by_code.get(row["ts_code"])
            if existing is None:
                row.setdefault("limit_up_days", 0)
                row.setdefault("limit_down_days", 0)
                row.setdefault("pools", [])
                row.setdefault("pool_reasons", [])
                rows_by_code[row["ts_code"]] = row
                return
            existing["limit_up_days"] = max(
                int(existing.get("limit_up_days") or 0),
                int(row.get("limit_up_days") or 0),
            )
            existing["limit_down_days"] = max(
                int(existing.get("limit_down_days") or 0),
                int(row.get("limit_down_days") or 0),
            )
            if row.get("pct_chg") is not None:
                existing["pct_chg"] = row["pct_chg"]
            if row.get("market") and not existing.get("market"):
                existing["market"] = row["market"]
            for pool in row.get("pools") or []:
                if pool not in (existing.get("pools") or []):
                    existing.setdefault("pools", []).append(pool)
            for reason in row.get("pool_reasons") or []:
                if reason not in (existing.get("pool_reasons") or []):
                    existing.setdefault("pool_reasons", []).append(reason)

        for row in self._collect_st_rows():
            merge(row)
        for row in self._collect_limit_up_rows(effective_date):
            merge(row)
        for row in self._collect_limit_down_rows(effective_date):
            merge(row)
        for row in self._collect_spot_pool_rows(effective_date):
            merge(row)
        for row in self._collect_st_omen_rows(effective_date):
            merge(row)

        rows = list(rows_by_code.values())
        logger.info(
            f"[RiskStockCollector] trade_date={effective_date} rows={len(rows)} "
            f"(st={sum(1 for r in rows if self._is_st_name(r.get('name', '')))}, "
            f"board2+={sum(1 for r in rows if int(r.get('limit_up_days') or 0) >= 2)}, "
            f"down2+={sum(1 for r in rows if int(r.get('limit_down_days') or 0) >= 2)}, "
            f"gain5={sum(1 for r in rows if '5%涨幅池' in (r.get('pools') or []))}, "
            f"gain9={sum(1 for r in rows if '9%涨幅池' in (r.get('pools') or []))}, "
            f"cx15={sum(1 for r in rows if '创业板大波动' in (r.get('pools') or []))}, "
            f"st_omen={sum(1 for r in rows if 'ST征兆' in (r.get('pools') or []))})"
        )
        return effective_date, rows

    def _resolve_trade_date(self) -> str:
        for offset in range(0, 8):
            candidate = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
            try:
                df = self._fetch_zt_pool(candidate)
            except Exception as exc:
                logger.warning(f"[RiskStockCollector] zt pool fetch failed for {candidate}: {exc}")
                continue
            if df is not None and not df.empty:
                return candidate
        return datetime.now().strftime("%Y%m%d")

    # ------------------------------------------------------------------
    # ST 名称池（已戴帽）
    # ------------------------------------------------------------------

    def _collect_st_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for item in self.snapshot_service._load_snapshot("A"):
            name = str(item.get("name") or "").strip()
            symbol = str(item.get("symbol") or "").strip()
            if not symbol or not name or not self._is_st_name(name):
                continue
            rows.append(
                {
                    "ts_code": to_ts_code(symbol),
                    "name": name,
                    "market": self._infer_market(symbol),
                    "limit_up_days": 0,
                }
            )
        return rows

    # ------------------------------------------------------------------
    # 连续涨停 / 连续跌停
    # ------------------------------------------------------------------

    def _collect_limit_up_rows(self, trade_date: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        try:
            df = self._fetch_zt_pool(trade_date)
        except Exception as exc:
            logger.warning(f"[RiskStockCollector] failed to load zt pool for {trade_date}: {exc}")
            return rows

        if df is None or df.empty:
            return rows

        for _, item in df.iterrows():
            limit_up_days = int(item.get("连板数") or 0)
            if limit_up_days < self.MIN_CONSECUTIVE_LIMIT_DAYS:
                continue
            code = str(item.get("代码") or "").strip()
            name = str(item.get("名称") or "").strip()
            if not code or not name:
                continue
            rows.append(
                {
                    "ts_code": to_ts_code(code),
                    "name": name,
                    "market": str(item.get("所属行业") or self._infer_market(code)),
                    "limit_up_days": limit_up_days,
                }
            )
        return rows

    def _collect_limit_down_rows(self, trade_date: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        try:
            df = self._fetch_dt_pool(trade_date)
        except Exception as exc:
            logger.warning(f"[RiskStockCollector] failed to load dt pool for {trade_date}: {exc}")
            return rows

        if df is None or df.empty:
            return rows

        for _, item in df.iterrows():
            limit_down_days = int(item.get("连续跌停") or 0)
            if limit_down_days < self.MIN_CONSECUTIVE_LIMIT_DAYS:
                continue
            code = str(item.get("代码") or "").strip()
            name = str(item.get("名称") or "").strip()
            if not code or not name:
                continue
            rows.append(
                {
                    "ts_code": to_ts_code(code),
                    "name": name,
                    "market": str(item.get("所属行业") or self._infer_market(code)),
                    "limit_down_days": limit_down_days,
                }
            )
        return rows

    # ------------------------------------------------------------------
    # 当日涨幅池（5% / 9%）+ 创业板大波动（回落自动移除：每次刷新重算）
    # ------------------------------------------------------------------

    def _collect_spot_pool_rows(self, trade_date: Optional[str] = None) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        try:
            df = self._fetch_spot(trade_date)
        except Exception as exc:
            logger.warning(f"[RiskStockCollector] failed to load spot quotes: {exc}")
            return rows

        if df is None or df.empty:
            return rows

        for _, item in df.iterrows():
            code = str(item.get("代码") or "").strip()
            name = str(item.get("名称") or "").strip()
            if not code or not name:
                continue
            try:
                pct = float(item.get("涨跌幅"))
            except (TypeError, ValueError):
                continue

            pools: List[str] = []
            reasons: List[str] = []
            if is_chinext(code) and abs(pct) >= self.CHINEXT_SWING:
                pools.append("创业板大波动")
                reasons.append(f"创业板当日涨跌幅 {pct:+.2f}%，波动达 ±{self.CHINEXT_SWING:.0f}%")
            if pct >= self.GAIN_POOL_9:
                pools.append("9%涨幅池")
                reasons.append(f"当日涨幅 {pct:.2f}%，达到 9% 档")
            elif pct >= self.GAIN_POOL_5:
                pools.append("5%涨幅池")
                reasons.append(f"当日涨幅 {pct:.2f}%，达到 5% 档")

            if not pools:
                continue
            rows.append(
                {
                    "ts_code": to_ts_code(code),
                    "name": name,
                    "market": self._infer_market(code),
                    "pct_chg": round(pct, 2),
                    "pools": pools,
                    "pool_reasons": reasons,
                }
            )
        return rows

    # ------------------------------------------------------------------
    # ST 征兆（年报预亏 / 净资产为负，未戴帽）
    # ------------------------------------------------------------------

    def _collect_st_omen_rows(self, trade_date: str) -> List[Dict[str, Any]]:
        cache_key = str(trade_date)[:8]
        with _st_omen_lock:
            cached = _st_omen_cache.get(cache_key)
        if cached is not None:
            return [dict(row) for row in cached]

        rows = self._build_st_omen_rows(trade_date)
        with _st_omen_lock:
            _st_omen_cache.clear()
            _st_omen_cache[cache_key] = [dict(row) for row in rows]
        return rows

    # 退市风险警示（*ST）财务口径的营收阈值：主板 3 亿，创业板/科创板 1 亿
    ST_REVENUE_MAIN = 3e8
    ST_REVENUE_GROWTH = 1e8

    def _build_st_omen_rows(self, trade_date: str) -> List[Dict[str, Any]]:
        name_map = self._build_name_map()
        omen_by_code: Dict[str, List[str]] = {}
        names_by_code: Dict[str, str] = {}

        # 1) 最近已披露年报：净利润为负且营收低于阈值（交易所退市风险警示口径）
        period, label = self._latest_disclosed_annual_period()
        try:
            df = self._fetch_yjbb(period)
        except Exception as exc:
            logger.warning(f"[RiskStockCollector] yjbb fetch failed for {period}: {exc}")
            df = None
        if df is not None and not df.empty:
            profit_col = "净利润-净利润"
            revenue_col = "营业总收入-营业总收入"
            if profit_col in df.columns and revenue_col in df.columns:
                seen: set = set()
                import math

                for _, item in df.iterrows():
                    code = str(item.get("股票代码") or "").strip().zfill(6)
                    if not code or code in seen:
                        continue
                    seen.add(code)
                    # 业绩报表混有新三板/北交所/老三板，ST 规则只适用沪深 A 股
                    if not self._is_sh_sz_a_share(code):
                        continue
                    try:
                        profit = float(item.get(profit_col))
                        revenue = float(item.get(revenue_col))
                    except (TypeError, ValueError):
                        continue
                    # NaN 会让所有比较判 False，必须显式排除，否则缺数据的票全部误入池
                    if not (math.isfinite(profit) and math.isfinite(revenue)):
                        continue
                    if profit >= 0:
                        continue
                    threshold = (
                        self.ST_REVENUE_GROWTH
                        if code.startswith(("300", "301", "688", "689"))
                        else self.ST_REVENUE_MAIN
                    )
                    if revenue >= threshold:
                        continue
                    ts_code = to_ts_code(code)
                    omen_by_code.setdefault(ts_code, []).append(
                        f"{label}净利润为负且营收低于 {threshold / 1e8:.0f} 亿（退市风险警示口径）"
                    )
                    name = str(item.get("股票简称") or "").strip()
                    if name:
                        names_by_code.setdefault(ts_code, name)

        # 2) 净资产为负（pb < 0），退市风险警示的直接口径之一
        try:
            basic_df = self._fetch_daily_basic_with_fallback(trade_date)
            if basic_df is not None and not basic_df.empty and "pb" in basic_df.columns:
                for _, item in basic_df.iterrows():
                    try:
                        pb = float(item.get("pb"))
                    except (TypeError, ValueError):
                        continue
                    if pb >= 0:
                        continue
                    ts_code = str(item.get("ts_code") or "").strip().upper()
                    if not ts_code:
                        continue
                    omen_by_code.setdefault(ts_code, []).append("净资产为负（PB<0）")
        except Exception as exc:
            logger.warning(f"[RiskStockCollector] daily_basic fetch failed: {exc}")

        rows: List[Dict[str, Any]] = []
        for ts_code, reasons in omen_by_code.items():
            symbol = ts_code.split(".")[0]
            name = names_by_code.get(ts_code) or name_map.get(symbol, "")
            if not name:
                continue
            # 已戴帽的归 ST股池，不重复进征兆池
            if self._is_st_name(name):
                continue
            rows.append(
                {
                    "ts_code": ts_code,
                    "name": name,
                    "market": self._infer_market(symbol),
                    "pools": ["ST征兆"],
                    "pool_reasons": reasons,
                }
            )
        return rows

    @staticmethod
    def _latest_disclosed_annual_period(now: Optional[datetime] = None) -> Tuple[str, str]:
        """最近已完整披露的年报期：年报 4 月底截止，5 月起用上一年，否则再往前一年。"""
        now = now or datetime.now()
        year = now.year - 1 if now.month >= 5 else now.year - 2
        return f"{year}1231", f"{year}年报"

    @staticmethod
    def _is_sh_sz_a_share(code: str) -> bool:
        """沪深 A 股（主板/创业板/科创板），排除新三板、北交所、老三板等。"""
        normalized = str(code).strip().zfill(6)
        return normalized.startswith(("600", "601", "603", "605", "000", "001", "002", "003", "300", "301", "688", "689"))

    def _fetch_daily_basic_with_fallback(self, trade_date: str):
        """当日盘中还没有 daily_basic 时回退最近一个有数据的交易日。"""
        from services.tushare.client import tushare_client

        tushare_client.ensure_initialized(log_missing_token=False)
        if not tushare_client.is_available:
            return None

        base = datetime.strptime(str(trade_date)[:8], "%Y%m%d")
        for offset in range(0, 8):
            candidate = (base - timedelta(days=offset)).strftime("%Y%m%d")
            df = tushare_client.query(
                "daily_basic",
                trade_date=candidate,
                fields="ts_code,pb",
            )
            if df is not None and not df.empty:
                return df
        return None

    def _build_name_map(self) -> Dict[str, str]:
        name_map: Dict[str, str] = {}
        try:
            for item in self.snapshot_service._load_snapshot("A"):
                symbol = str(item.get("symbol") or "").strip()
                name = str(item.get("name") or "").strip()
                if symbol and name:
                    name_map[symbol] = name
        except Exception as exc:
            logger.warning(f"[RiskStockCollector] name map build failed: {exc}")
        return name_map

    # ------------------------------------------------------------------
    # 数据源封装（便于测试 monkeypatch）
    # ------------------------------------------------------------------

    def _fetch_zt_pool(self, trade_date: str):
        import akshare as ak

        return ak.stock_zt_pool_em(date=trade_date)

    def _fetch_dt_pool(self, trade_date: str):
        import akshare as ak

        # 东财「跌停股池」，列含 代码/名称/连续跌停/所属行业
        return ak.stock_zt_pool_dtgc_em(date=trade_date)

    # 东财行情主机：push2 容易拒连（本地/服务器均复现过 Server disconnected），
    # 按顺序故障转移；push2delay 为延时源，作为兜底足够 15 分钟级别的池子刷新。
    SPOT_HOSTS = (
        "push2.eastmoney.com",
        "82.push2.eastmoney.com",
        "push2delay.eastmoney.com",
    )
    # 沪深 A 股（深主板/创业板/沪主板/科创板），不含北交所
    SPOT_FS = "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23"
    SPOT_PAGE_SIZE = 100
    SPOT_MAX_PAGES = 40

    def _fetch_spot(self, trade_date: Optional[str] = None):
        """全市场涨跌幅快照。

        东财 → 新浪 → tushare daily → akshare 四级回退：
        - 服务器（海外 IP）对东财 push2 系列经常被拒连
        - 新浪行情从服务器一直可用（实时价补丁同源），盘中主力兜底
        - tushare daily 是积分接口、最稳，但只有收盘结算后才有当日数据，
          用于 16:10 定稿任务的兜底（盘中返回空会自然跳过）
        """
        try:
            df = self._fetch_spot_eastmoney()
            if df is not None and not df.empty:
                return df
        except Exception as exc:
            logger.warning(f"[RiskStockCollector] eastmoney spot fetch failed: {exc}")

        try:
            df = self._fetch_spot_sina()
            if df is not None and not df.empty:
                return df
        except Exception as exc:
            logger.warning(f"[RiskStockCollector] sina spot fetch failed: {exc}")

        try:
            df = self._fetch_spot_tushare(trade_date)
            if df is not None and not df.empty:
                return df
        except Exception as exc:
            logger.warning(f"[RiskStockCollector] tushare spot fetch failed: {exc}")

        import akshare as ak

        return ak.stock_zh_a_spot_em()

    def _fetch_spot_tushare(self, trade_date: Optional[str] = None):
        """tushare pro.daily 全市场单日行情（收盘结算后可用）。"""
        import pandas as pd

        from services.tushare.client import tushare_client

        tushare_client.ensure_initialized(log_missing_token=False)
        if not tushare_client.is_available:
            return None

        effective = str(trade_date or datetime.now().strftime("%Y%m%d"))[:8]
        df = tushare_client.query(
            "daily",
            trade_date=effective,
            fields="ts_code,pct_chg",
        )
        if df is None or df.empty:
            return None

        name_map = self._build_name_map()
        rows: List[Dict[str, Any]] = []
        for _, item in df.iterrows():
            ts_code = str(item.get("ts_code") or "").strip().upper()
            symbol = ts_code.split(".")[0]
            if not symbol or not self._is_sh_sz_a_share(symbol):
                continue
            try:
                pct = float(item.get("pct_chg"))
            except (TypeError, ValueError):
                continue
            # 快照名称缺失时用代码兜底，不让 tushare 兜底链依赖快照健康度
            name = name_map.get(symbol, "") or symbol
            rows.append({"代码": symbol, "名称": name, "涨跌幅": round(pct, 2)})

        return pd.DataFrame(rows, columns=["代码", "名称", "涨跌幅"])

    def _fetch_spot_eastmoney(self):
        import pandas as pd
        import requests

        session = requests.Session()
        session.trust_env = False

        rows: List[Dict[str, Any]] = []
        seen: set = set()

        # 涨幅从高到低翻页，跌破 5% 档即停（覆盖 5%/9% 池 + 创业板暴涨）
        for item in self._page_spot(session, ascending=False):
            pct = item["涨跌幅"]
            if pct < self.GAIN_POOL_5:
                break
            if item["代码"] not in seen:
                seen.add(item["代码"])
                rows.append(item)

        # 跌幅从低到高翻页，回到 -15% 以内即停（只为创业板大波动的下跌侧）
        for item in self._page_spot(session, ascending=True):
            pct = item["涨跌幅"]
            if pct > -self.CHINEXT_SWING:
                break
            if item["代码"] not in seen:
                seen.add(item["代码"])
                rows.append(item)

        return pd.DataFrame(rows, columns=["代码", "名称", "涨跌幅"])

    SINA_PAGE_SIZE = 80
    SINA_MAX_PAGES = 40

    def _fetch_spot_sina(self):
        """新浪行情中心列表：按涨跌幅排序分页，阈值早停，与东财路径同构。"""
        import pandas as pd
        import requests

        session = requests.Session()
        session.trust_env = False

        rows: List[Dict[str, Any]] = []
        seen: set = set()

        for item in self._page_spot_sina(session, ascending=False):
            if item["涨跌幅"] < self.GAIN_POOL_5:
                break
            if item["代码"] not in seen:
                seen.add(item["代码"])
                rows.append(item)

        for item in self._page_spot_sina(session, ascending=True):
            if item["涨跌幅"] > -self.CHINEXT_SWING:
                break
            if item["代码"] not in seen:
                seen.add(item["代码"])
                rows.append(item)

        return pd.DataFrame(rows, columns=["代码", "名称", "涨跌幅"])

    def _page_spot_sina(self, session, ascending: bool):
        for page in range(1, self.SINA_MAX_PAGES + 1):
            data = self._fetch_sina_page(session, page=page, ascending=ascending)
            if not data:
                return
            for entry in data:
                code = str(entry.get("code") or "").strip()
                name = str(entry.get("name") or "").strip()
                pct = entry.get("changepercent")
                try:
                    pct = float(pct)
                except (TypeError, ValueError):
                    continue
                if not code or not name:
                    continue
                # 新浪 hs_a 含北交所（8/4/92 开头），涨幅池只关注沪深 A 股
                if not self._is_sh_sz_a_share(code):
                    continue
                yield {"代码": code, "名称": name, "涨跌幅": pct}
            if len(data) < self.SINA_PAGE_SIZE:
                return

    def _fetch_sina_page(self, session, page: int, ascending: bool) -> List[Dict[str, Any]]:
        url = (
            "https://vip.stock.finance.sina.com.cn/quotes_service/api/"
            "json_v2.php/Market_Center.getHQNodeData"
        )
        params = {
            "page": page,
            "num": self.SINA_PAGE_SIZE,
            "sort": "changepercent",
            "asc": 1 if ascending else 0,
            "node": "hs_a",
            "symbol": "",
            "_s_r_a": "page",
        }
        headers = {
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0",
        }
        resp = session.get(url, params=params, headers=headers, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    def _page_spot(self, session, ascending: bool):
        """按涨跌幅排序逐页产出 {代码, 名称, 涨跌幅}。"""
        for page in range(1, self.SPOT_MAX_PAGES + 1):
            diff = self._fetch_spot_page(session, page=page, ascending=ascending)
            if not diff:
                return
            for entry in diff:
                code = str(entry.get("f12") or "").strip()
                name = str(entry.get("f14") or "").strip()
                pct = entry.get("f3")
                if not code or not name or not isinstance(pct, (int, float)):
                    continue
                yield {"代码": code, "名称": name, "涨跌幅": float(pct)}
            if len(diff) < self.SPOT_PAGE_SIZE:
                return

    def _fetch_spot_page(self, session, page: int, ascending: bool) -> List[Dict[str, Any]]:
        params = {
            "pn": page,
            "pz": self.SPOT_PAGE_SIZE,
            "po": 0 if ascending else 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": self.SPOT_FS,
            "fields": "f2,f3,f12,f14",
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://quote.eastmoney.com/",
        }
        last_error: Optional[Exception] = None
        for host in self.SPOT_HOSTS:
            try:
                resp = session.get(
                    f"https://{host}/api/qt/clist/get",
                    params=params,
                    headers=headers,
                    timeout=12,
                    verify=False,
                )
                resp.raise_for_status()
                data = (resp.json() or {}).get("data") or {}
                return data.get("diff") or []
            except Exception as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        return []

    def _fetch_yjbb(self, period: str):
        import akshare as ak

        # 东财「业绩报表」（实际披露值），列含 股票代码/股票简称/净利润-净利润/营业总收入-营业总收入
        return ak.stock_yjbb_em(date=period)

    def _infer_market(self, code: str) -> str:
        normalized = str(code).strip().zfill(6)
        if normalized.startswith("688"):
            return "科创板"
        if normalized.startswith(("300", "301")):
            return "创业板"
        if normalized.startswith(("8", "4")):
            return "北交所"
        return "主板"

    def _is_st_name(self, name: str) -> bool:
        normalized = name.upper().replace("＊", "*")
        return "ST" in normalized
