"""
Collect daily risk stock candidates from public market data sources.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from services.search_snapshot_service import SearchSnapshotService
from utils.logger import get_logger

logger = get_logger()


def to_ts_code(code: str) -> str:
    normalized = str(code).strip().zfill(6)
    if normalized.startswith("6"):
        return f"{normalized}.SH"
    return f"{normalized}.SZ"


class RiskStockCollector:
    """Build risk-stock source rows from A-share snapshot and limit-up pool."""

    def __init__(self, snapshot_service: Optional[SearchSnapshotService] = None):
        self.snapshot_service = snapshot_service or SearchSnapshotService()

    def collect_rows(self, trade_date: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
        effective_date = trade_date or self._resolve_trade_date()
        rows_by_code: Dict[str, Dict[str, Any]] = {}

        for row in self._collect_st_rows():
            rows_by_code[row["ts_code"]] = row

        for row in self._collect_limit_up_rows(effective_date):
            existing = rows_by_code.get(row["ts_code"])
            if existing:
                existing["limit_up_days"] = max(
                    int(existing.get("limit_up_days") or 0),
                    int(row.get("limit_up_days") or 0),
                )
                if row.get("market") and not existing.get("market"):
                    existing["market"] = row["market"]
            else:
                rows_by_code[row["ts_code"]] = row

        rows = list(rows_by_code.values())
        logger.info(
            f"[RiskStockCollector] trade_date={effective_date} rows={len(rows)} "
            f"(st={sum(1 for row in rows if self._is_st_name(row.get('name', '')))}, "
            f"board3+={sum(1 for row in rows if int(row.get('limit_up_days') or 0) >= 3)})"
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
            if limit_up_days < 3:
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

    def _fetch_zt_pool(self, trade_date: str):
        import akshare as ak

        return ak.stock_zt_pool_em(date=trade_date)

    def _infer_market(self, code: str) -> str:
        normalized = str(code).strip().zfill(6)
        if normalized.startswith("688"):
            return "科创板"
        if normalized.startswith("300"):
            return "创业板"
        if normalized.startswith(("8", "4")):
            return "北交所"
        return "主板"

    def _is_st_name(self, name: str) -> bool:
        normalized = name.upper().replace("＊", "*")
        return "ST" in normalized
