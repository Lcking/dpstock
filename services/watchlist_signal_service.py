"""
Watchlist structure signal scanning.

盘后扫描所有用户观察池标的，检测结构信号（均线交叉 / MA20 突破 / 放量异动），
生成站内提醒。复用与风险提醒一致的 inbox 管道，仅做研究型观察提示，不构成建议。
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from database.db_factory import DatabaseFactory
from utils.logger import get_logger

logger = get_logger()

# 单次扫描的标的上限，防止观察池膨胀拖垮盘后任务
MAX_SYMBOLS_PER_SCAN = 300
# 最新 bar 距今超过该天数视为数据过期，不产生信号
MAX_STALE_DAYS = 5

SIGNAL_LABELS = {
    "golden_cross": "MA5 上穿 MA20（金叉）",
    "death_cross": "MA5 下穿 MA20（死叉）",
    "ma20_breakout_up": "放量站上 MA20",
    "ma20_breakdown": "跌破 MA20",
    "volume_spike": "成交量显著放大",
}


class WatchlistSignalService:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            DatabaseFactory.initialize(db_path)
        self.db = DatabaseFactory

    # ------------------------------------------------------------------
    # Scan & sync
    # ------------------------------------------------------------------

    def scan_and_sync(self) -> Dict[str, Any]:
        """扫描观察池标的并写入信号提醒。返回统计信息。"""
        symbol_users = self._collect_watchlist_symbols()
        if not symbol_users:
            return {"symbols": 0, "signals": 0, "created": 0, "matched_users": 0}

        codes = list(symbol_users.keys())[:MAX_SYMBOLS_PER_SCAN]
        signals_by_code = self._scan_symbols(codes)

        created = 0
        matched_users = set()
        now = datetime.utcnow().isoformat() + "Z"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for ts_code, signals in signals_by_code.items():
                entry = symbol_users.get(ts_code)
                if not entry:
                    continue
                for signal in signals:
                    for user_id in entry["user_ids"]:
                        cursor.execute(
                            """
                            INSERT INTO watchlist_signal_alerts (
                                id, user_id, ts_code, stock_name, trade_date,
                                signal_type, title, detail, created_at, read_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                            ON CONFLICT(user_id, ts_code, trade_date, signal_type) DO NOTHING
                            """,
                            (
                                f"wsa_{uuid.uuid4().hex[:12]}",
                                user_id,
                                ts_code,
                                entry.get("name") or ts_code,
                                signal["trade_date"],
                                signal["signal_type"],
                                signal["title"],
                                signal["detail"],
                                now,
                            ),
                        )
                        if cursor.rowcount > 0:
                            created += 1
                            matched_users.add(user_id)
            conn.commit()

        total_signals = sum(len(v) for v in signals_by_code.values())
        logger.info(
            f"[WatchlistSignal] symbols={len(codes)} signals={total_signals} "
            f"created={created} users={len(matched_users)}"
        )
        return {
            "symbols": len(codes),
            "signals": total_signals,
            "created": created,
            "matched_users": len(matched_users),
        }

    def _collect_watchlist_symbols(self) -> Dict[str, Dict[str, Any]]:
        """收集全部观察池标的 -> {ts_code: {user_ids: set, name: str}}。"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT w.user_id, wi.ts_code, wi.name
                FROM watchlist_items wi
                JOIN watchlists w ON w.id = wi.watchlist_id
                """
            )
            rows = [dict(row) for row in cursor.fetchall()]

        symbols: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            ts_code = str(row.get("ts_code") or "").strip()
            user_id = row.get("user_id")
            if not ts_code or not user_id:
                continue
            entry = symbols.setdefault(ts_code, {"user_ids": set(), "name": ""})
            entry["user_ids"].add(user_id)
            if not entry["name"] and row.get("name"):
                entry["name"] = str(row["name"])
        return symbols

    def _scan_symbols(self, ts_codes: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """批量拉取行情并检测信号。"""
        from services.stock_data_provider import StockDataProvider

        provider = StockDataProvider()
        # 代码内部会做 normalize + 市场推断（含 ETF/LOF）
        data_map = asyncio.run(
            provider.get_multiple_stocks_data(ts_codes, market_type="A", max_concurrency=5)
        )

        results: Dict[str, List[Dict[str, Any]]] = {}
        for ts_code, df in (data_map or {}).items():
            try:
                if df is None or getattr(df, "empty", True):
                    continue
                signals = self.detect_signals(df)
                if signals:
                    # data_map 的 key 是 normalize 后的代码，映射回原 ts_code
                    original = next(
                        (c for c in ts_codes if c.split(".")[0] == str(ts_code).split(".")[0]),
                        str(ts_code),
                    )
                    results[original] = signals
            except Exception as exc:
                logger.warning(f"[WatchlistSignal] detect failed for {ts_code}: {exc}")
        return results

    # ------------------------------------------------------------------
    # Signal detection (pure function on OHLCV DataFrame)
    # ------------------------------------------------------------------

    def detect_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        对最新一根 K 线检测结构信号。

        要求 df 含 Close/Volume 列、DatetimeIndex（或可转），至少 25 行。
        """
        if df is None or len(df) < 25:
            return []

        df = df.sort_index()
        closes = df["Close"].astype(float)
        volumes = df["Volume"].astype(float)

        ma5 = closes.rolling(5).mean()
        ma20 = closes.rolling(20).mean()
        vol20 = volumes.rolling(20).mean().shift(1)  # 不含当日

        last_date = self._bar_date(df.index[-1])
        if last_date is None or self._is_stale(last_date):
            return []

        i = len(df) - 1
        prev = i - 1
        if pd.isna(ma20.iloc[i]) or pd.isna(ma20.iloc[prev]) or pd.isna(ma5.iloc[prev]):
            return []

        close_now = float(closes.iloc[i])
        close_prev = float(closes.iloc[prev])
        ma20_now = float(ma20.iloc[i])
        ma20_prev = float(ma20.iloc[prev])
        ma5_now = float(ma5.iloc[i])
        ma5_prev = float(ma5.iloc[prev])
        vol_now = float(volumes.iloc[i])
        vol_base = float(vol20.iloc[i]) if not pd.isna(vol20.iloc[i]) else 0.0
        vol_ratio = (vol_now / vol_base) if vol_base > 0 else 0.0
        pct_chg = (close_now - close_prev) / close_prev * 100 if close_prev else 0.0

        signals: List[Dict[str, Any]] = []

        def add(signal_type: str, detail: str) -> None:
            signals.append({
                "signal_type": signal_type,
                "title": SIGNAL_LABELS[signal_type],
                "detail": detail + " 该信号为结构观察提示，不构成投资建议。",
                "trade_date": last_date,
            })

        if ma5_prev <= ma20_prev and ma5_now > ma20_now:
            add(
                "golden_cross",
                f"MA5（{ma5_now:.2f}）上穿 MA20（{ma20_now:.2f}），收盘价 {close_now:.2f}。",
            )
        elif ma5_prev >= ma20_prev and ma5_now < ma20_now:
            add(
                "death_cross",
                f"MA5（{ma5_now:.2f}）下穿 MA20（{ma20_now:.2f}），收盘价 {close_now:.2f}。",
            )

        if close_prev <= ma20_prev and close_now > ma20_now and vol_ratio >= 1.5:
            add(
                "ma20_breakout_up",
                f"收盘价 {close_now:.2f} 站上 MA20（{ma20_now:.2f}），"
                f"成交量约为 20 日均量的 {vol_ratio:.1f} 倍。",
            )
        elif close_prev >= ma20_prev and close_now < ma20_now:
            add(
                "ma20_breakdown",
                f"收盘价 {close_now:.2f} 跌破 MA20（{ma20_now:.2f}），当日涨跌 {pct_chg:+.1f}%。",
            )

        if vol_ratio >= 2.5 and abs(pct_chg) >= 2.0:
            add(
                "volume_spike",
                f"成交量约为 20 日均量的 {vol_ratio:.1f} 倍，当日涨跌 {pct_chg:+.1f}%。",
            )

        return signals

    @staticmethod
    def _bar_date(raw: Any) -> Optional[str]:
        try:
            return pd.Timestamp(raw).strftime("%Y-%m-%d")
        except Exception:
            return None

    @staticmethod
    def _is_stale(bar_date: str) -> bool:
        try:
            latest = datetime.strptime(bar_date, "%Y-%m-%d")
        except ValueError:
            return True
        return datetime.now() - latest > timedelta(days=MAX_STALE_DAYS)

    # ------------------------------------------------------------------
    # Alert accessors (mirror WatchlistRiskAlertService)
    # ------------------------------------------------------------------

    @staticmethod
    def _table_exists(cursor) -> bool:
        row = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist_signal_alerts'"
        ).fetchone()
        return bool(row)

    def get_unread_count(self, user_id: str) -> int:
        if not user_id:
            return 0
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if not self._table_exists(cursor):
                return 0
            cursor.execute(
                """
                SELECT COUNT(*) AS c
                FROM watchlist_signal_alerts
                WHERE user_id = ? AND read_at IS NULL
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        return int(row.get("c") or 0) if row else 0

    def list_alerts(self, user_id: str, limit: int = 20, unread_only: bool = False) -> Dict[str, Any]:
        limit = min(max(int(limit or 20), 1), 100)
        if not user_id:
            return {"unread_count": 0, "items": []}

        unread_count = self.get_unread_count(user_id)
        query = """
            SELECT *
            FROM watchlist_signal_alerts
            WHERE user_id = ?
        """
        params: List[Any] = [user_id]
        if unread_only:
            query += " AND read_at IS NULL"
        query += " ORDER BY created_at DESC, trade_date DESC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if not self._table_exists(cursor):
                return {"unread_count": 0, "items": []}
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]

        return {"unread_count": unread_count, "items": rows}

    def mark_all_read(self, user_id: str) -> Dict[str, Any]:
        if not user_id:
            return {"updated": 0}
        now = datetime.utcnow().isoformat() + "Z"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if not self._table_exists(cursor):
                return {"updated": 0}
            cursor.execute(
                """
                UPDATE watchlist_signal_alerts
                SET read_at = ?
                WHERE user_id = ? AND read_at IS NULL
                """,
                (now, user_id),
            )
            updated = cursor.rowcount
            conn.commit()
        return {"updated": updated}
