"""
A-share industry lookup with in-memory + optional file cache.
Used by watchlist portfolio health (industry exposure / concentration).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from utils.logger import get_logger

logger = get_logger()

CACHE_MAX_AGE_DAYS = 7


class AShareIndustryLookup:
    _industry_by_code: Dict[str, str] = {}
    _loaded: bool = False

    @classmethod
    def lookup(cls, ts_code: str) -> Optional[str]:
        code = cls._normalize_code(ts_code)
        if not code:
            return None
        cls._ensure_loaded()
        return cls._industry_by_code.get(code)

    @classmethod
    def get_map(cls) -> Dict[str, str]:
        cls._ensure_loaded()
        return dict(cls._industry_by_code)

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls._loaded:
            return
        cache_path = cls._cache_path()
        cached = cls._read_cache_file(cache_path)
        if cached:
            cls._industry_by_code = cached
            cls._loaded = True
            return

        loaded = cls._load_from_tushare() or cls._load_from_akshare()
        cls._industry_by_code = loaded
        cls._loaded = True
        if loaded:
            cls._write_cache_file(cache_path, loaded)

    @classmethod
    def _cache_path(cls) -> Path:
        repo_root = Path(__file__).resolve().parents[1]
        return repo_root / "data" / "industry_map.json"

    @classmethod
    def _read_cache_file(cls, path: Path) -> Optional[Dict[str, str]]:
        try:
            if not path.exists():
                return None
            payload = json.loads(path.read_text(encoding="utf-8"))
            updated_at = payload.get("updated_at")
            rows = payload.get("rows") or {}
            if not rows or not updated_at:
                return None
            updated = datetime.fromisoformat(str(updated_at))
            if datetime.utcnow() - updated > timedelta(days=CACHE_MAX_AGE_DAYS):
                return None
            return {str(k): str(v) for k, v in rows.items() if k and v}
        except Exception:
            return None

    @classmethod
    def _write_cache_file(cls, path: Path, rows: Dict[str, str]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = path.with_suffix(path.suffix + ".tmp")
            temp_path.write_text(
                json.dumps(
                    {
                        "updated_at": datetime.utcnow().isoformat(),
                        "rows": rows,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            temp_path.replace(path)
        except Exception as e:
            logger.warning(f"[IndustryLookup] Failed to write cache: {e}")

    @classmethod
    def _load_from_tushare(cls) -> Dict[str, str]:
        try:
            from services.tushare.client import tushare_client

            tushare_client.ensure_initialized(log_missing_token=False)
            if not tushare_client.is_available:
                return {}
            df = tushare_client.get_stock_basic()
            if df is None or df.empty:
                return {}
            rows: Dict[str, str] = {}
            for _, row in df.iterrows():
                code = cls._normalize_code(row.get("ts_code"))
                industry = str(row.get("industry") or "").strip()
                if code and industry:
                    rows[code] = industry
            logger.info(f"[IndustryLookup] Loaded {len(rows)} industries from tushare")
            return rows
        except Exception as e:
            logger.warning(f"[IndustryLookup] tushare load failed: {e}")
            return {}

    @classmethod
    def _load_from_akshare(cls) -> Dict[str, str]:
        try:
            import concurrent.futures

            import akshare as ak

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(ak.stock_board_industry_name_em)
                board_df = future.result(timeout=15)
            if board_df is None or board_df.empty:
                return {}

            rows: Dict[str, str] = {}
            for board_name in board_df["板块名称"].dropna().astype(str).tolist()[:30]:
                try:
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(ak.stock_board_industry_cons_em, symbol=board_name)
                        cons_df = future.result(timeout=10)
                    if cons_df is None or cons_df.empty:
                        continue
                    code_col = "代码" if "代码" in cons_df.columns else cons_df.columns[0]
                    for code in cons_df[code_col].dropna().astype(str).tolist():
                        normalized = cls._normalize_code(code)
                        if normalized:
                            rows.setdefault(normalized, board_name)
                except Exception:
                    continue
            if rows:
                logger.info(f"[IndustryLookup] Loaded {len(rows)} industries from akshare boards")
            return rows
        except Exception as e:
            logger.warning(f"[IndustryLookup] akshare load failed: {e}")
            return {}

    @classmethod
    def _normalize_code(cls, raw: object) -> str:
        text = str(raw or "").strip().upper()
        if not text:
            return ""
        return text.split(".")[0]
