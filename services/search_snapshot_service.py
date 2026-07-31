import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.stock_data_provider import StockDataProvider
from services.us_stock_service_async import POPULAR_US_STOCKS
from utils.logger import get_logger

logger = get_logger()

MIN_A_SHARE_SNAPSHOT_COUNT = 4500

POPULAR_HK_STOCKS = [
    ("00700", "腾讯控股"), ("00388", "香港交易所"), ("00939", "建设银行"),
    ("00941", "中国移动"), ("01299", "友邦保险"), ("02318", "中国平安"),
    ("03690", "美团"), ("00175", "吉利汽车"), ("01810", "小米集团"),
    ("00883", "中国海洋石油"), ("00005", "汇丰控股"), ("02020", "安踏体育"),
    ("01093", "石药集团"), ("00027", "银河娱乐"), ("01024", "快手"),
    ("03968", "招商银行"), ("01398", "工商银行"), ("00386", "中国石油化工"),
    ("01288", "农业银行"), ("03988", "中国银行"), ("00688", "中国海外发展"),
    ("02382", "舜宇光学科技"), ("00384", "中国燃气"), ("02269", "药明生物"),
    ("00291", "华润啤酒"), ("01109", "华润置地"), ("00016", "新鸿基地产"),
    ("00001", "长和"), ("00002", "中电控股"), ("00003", "香港中华煤气"),
]


class SearchSnapshotService:
    def __init__(
        self,
        snapshot_dir: Optional[Path] = None,
        provider_factory=StockDataProvider,
    ):
        repo_root = Path(__file__).resolve().parents[1]
        self.snapshot_dir = Path(snapshot_dir or repo_root / "data" / "search_snapshots")
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.provider_factory = provider_factory
        self._cache: Dict[str, List[Dict[str, str]]] = {}
        self._cache_mtime: Dict[str, float] = {}
        self._bootstrap_static_snapshots()

    def _snapshot_path(self, market: str) -> Path:
        filename_map = {
            "A": "a_shares.json",
            "HK": "hk_shares.json",
            "US": "us_stocks.json",
        }
        return self.snapshot_dir / filename_map[market]

    def _bootstrap_static_snapshots(self) -> None:
        if not self._snapshot_path("HK").exists():
            self._write_snapshot(
                "HK",
                [
                    self._normalize_row({"symbol": code, "name": name}, "HK")
                    for code, name in POPULAR_HK_STOCKS
                ],
            )
        if not self._snapshot_path("US").exists():
            self._write_snapshot(
                "US",
                [
                    self._normalize_row({"symbol": row["symbol"], "name": row["name"]}, "US")
                    for row in POPULAR_US_STOCKS
                ],
            )

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower())

    def _build_pinyin(self, name: str) -> str:
        try:
            from pypinyin import Style, pinyin

            letters = pinyin(name, style=Style.FIRST_LETTER)
            return "".join(item[0] for item in letters).lower()
        except Exception:
            return self._normalize_text(name)

    def _normalize_row(self, row: Dict[str, Any], market: str) -> Dict[str, str]:
        symbol = str(row.get("symbol") or row.get("code") or "").strip()
        name = str(row.get("name") or symbol).strip()
        pinyin = str(row.get("pinyin") or self._build_pinyin(name)).strip().lower()
        return {
            "symbol": symbol,
            "name": name,
            "market": market,
            "pinyin": pinyin,
        }

    def _write_snapshot(self, market: str, rows: List[Dict[str, str]]) -> None:
        path = self._snapshot_path(market)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(path)
        self._cache[market] = rows
        self._cache_mtime[market] = path.stat().st_mtime

    def _load_snapshot(self, market: str) -> List[Dict[str, str]]:
        path = self._snapshot_path(market)
        if not path.exists():
            return []

        mtime = path.stat().st_mtime
        if market in self._cache and self._cache_mtime.get(market) == mtime:
            return self._cache[market]

        rows = json.loads(path.read_text(encoding="utf-8"))
        normalized_rows = [self._normalize_row(row, market) for row in rows]
        self._cache[market] = normalized_rows
        self._cache_mtime[market] = mtime
        return normalized_rows

    def ensure_a_share_snapshot(self, min_count: int = MIN_A_SHARE_SNAPSHOT_COUNT) -> int:
        """Refresh A-share snapshot when cached list is missing or too small."""
        current = self._load_snapshot("A")
        if len(current) >= min_count:
            return len(current)
        refreshed = self.refresh_a_share_snapshot()
        if refreshed > 0:
            return refreshed
        return len(self._load_snapshot("A"))

    def refresh_a_share_snapshot(self) -> int:
        try:
            # 强制绕过进程内共享缓存，避免新股上市后仍写回旧列表
            if hasattr(self.provider_factory, "clear_a_share_list_cache"):
                self.provider_factory.clear_a_share_list_cache()
            provider = self.provider_factory()
            rows = provider.get_a_share_list(force_refresh=True)
            normalized_rows = [
                self._normalize_row(row, "A")
                for row in rows
                if row.get("code") or row.get("symbol")
            ]
            if normalized_rows:
                self._write_snapshot("A", normalized_rows)
                logger.info(f"[SearchSnapshot] Refreshed A-share snapshot with {len(normalized_rows)} rows")
                return len(normalized_rows)
        except Exception as e:
            logger.warning(f"[SearchSnapshot] Failed to refresh A-share snapshot: {e}")
        return 0

    @staticmethod
    def _strip_listing_prefix(name: str) -> str:
        """去掉新股临时代码前缀：C长鑫 → 长鑫，N泰诺 → 泰诺。"""
        text = str(name or "").strip()
        if len(text) >= 2 and text[0] in {"C", "N", "c", "n"} and "\u4e00" <= text[1] <= "\u9fff":
            return text[1:]
        return text

    def _row_matches_keyword(self, row: Dict[str, str], keyword: str) -> bool:
        lowered = keyword.lower()
        name = row.get("name") or ""
        bare_name = self._strip_listing_prefix(name)
        return (
            lowered in row["symbol"].lower()
            or lowered in name.lower()
            or lowered in bare_name.lower()
            or bare_name.lower() in lowered
            or lowered in row.get("pinyin", "")
        )

    def _search_market(self, market: str, keyword: str, limit: int) -> List[Dict[str, str]]:
        trimmed = keyword.strip()
        if not trimmed:
            return []

        rows = self._load_snapshot(market)
        results: List[Dict[str, str]] = []
        for row in rows:
            if self._row_matches_keyword(row, trimmed):
                results.append(
                    {
                        "symbol": row["symbol"],
                        "name": row["name"],
                        "market": row["market"],
                    }
                )
                if len(results) >= limit:
                    break
        return results

    def _resolve_a_share_name(self, symbol: str) -> str:
        """快照缺失时用 tushare 补名称，避免搜索只显示代码。"""
        try:
            from services.tushare.client import tushare_client

            tushare_client.ensure_initialized(log_missing_token=False)
            if not tushare_client.is_available:
                return ""
            ts_code = f"{symbol}.SH" if symbol.startswith(("6", "9")) else f"{symbol}.SZ"
            df = tushare_client.get_stock_basic(ts_code)
            if df is not None and not df.empty:
                return str(df.iloc[0].get("name") or "").strip()
        except Exception as exc:
            logger.debug(f"[SearchSnapshot] resolve name failed for {symbol}: {exc}")
        return ""

    def search_a_shares(self, keyword: str, limit: int = 10) -> List[Dict[str, str]]:
        trimmed = keyword.strip()
        if trimmed.isdigit() and len(trimmed) == 6:
            rows = self._load_snapshot("A")
            for row in rows:
                if row["symbol"] == trimmed:
                    return [{"symbol": row["symbol"], "name": row["name"], "market": "A"}]
            name = self._resolve_a_share_name(trimmed) or trimmed
            return [{"symbol": trimmed, "name": name, "market": "A"}]
        return self._search_market("A", trimmed, limit)

    def search_hk_shares(self, keyword: str, limit: int = 10) -> List[Dict[str, str]]:
        return self._search_market("HK", keyword, limit)

    def search_us_stocks(self, keyword: str, limit: int = 10) -> List[Dict[str, str]]:
        return self._search_market("US", keyword, limit)

    def search_global(self, keyword: str, market_type: str = "ALL", limit_per_market: int = 5) -> List[Dict[str, str]]:
        markets: List[str]
        if market_type == "ALL":
            markets = ["A", "HK", "US"]
        elif market_type in {"A", "HK", "US"}:
            markets = [market_type]
        else:
            markets = []

        results: List[Dict[str, str]] = []
        for market in markets:
            if market == "A":
                market_results = self.search_a_shares(keyword, limit_per_market)
            elif market == "HK":
                market_results = self.search_hk_shares(keyword, limit_per_market)
            else:
                market_results = self.search_us_stocks(keyword, limit_per_market)

            for row in market_results:
                results.append(
                    {
                        "label": f"{row['name']} ({row['symbol']})",
                        "value": row["symbol"],
                        "market": row["market"],
                        "name": row["name"],
                    }
                )
        return results
