import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db_factory import DatabaseFactory
from services.risk_stock_collector import RiskStockCollector
from utils.logger import get_logger

logger = get_logger()


class RiskStockService:
    """Daily risk stock list service."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        collector: Optional[RiskStockCollector] = None,
    ):
        if db_path:
            DatabaseFactory.initialize(db_path)
        self.db = DatabaseFactory
        self.collector = collector or RiskStockCollector()

    def refresh_from_rows(self, trade_date: str, rows: List[Dict[str, Any]], source: str = "manual") -> Dict[str, Any]:
        items = []
        for row in rows:
            item = self._classify_row(trade_date, row, source=source)
            if item:
                items.append(item)

        now = datetime.utcnow().isoformat() + "Z"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # 替换式刷新：5%/9% 涨幅池等动态池要求「回落自动移除」，
            # 所以每次刷新以最新快照整体替换当日清单。
            # 空结果通常意味着数据源故障，此时保留旧数据不做清空。
            if items:
                cursor.execute(
                    "DELETE FROM risk_stock_items WHERE trade_date = ?",
                    (trade_date,),
                )
            for item in items:
                cursor.execute(
                    """
                    INSERT INTO risk_stock_items (
                        trade_date, ts_code, name, market, tags_json, risk_level,
                        reason, limit_up_days, limit_down_days, pct_chg,
                        is_st, source, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(trade_date, ts_code)
                    DO UPDATE SET
                        name = excluded.name,
                        market = excluded.market,
                        tags_json = excluded.tags_json,
                        risk_level = excluded.risk_level,
                        reason = excluded.reason,
                        limit_up_days = excluded.limit_up_days,
                        limit_down_days = excluded.limit_down_days,
                        pct_chg = excluded.pct_chg,
                        is_st = excluded.is_st,
                        source = excluded.source,
                        updated_at = excluded.updated_at
                    """,
                    (
                        item["trade_date"],
                        item["ts_code"],
                        item["name"],
                        item["market"],
                        json.dumps(item["tags"], ensure_ascii=False),
                        item["risk_level"],
                        item["reason"],
                        item["limit_up_days"],
                        item["limit_down_days"],
                        item["pct_chg"],
                        1 if item["is_st"] else 0,
                        item["source"],
                        now,
                        now,
                    ),
                )
            conn.commit()

        result = {"trade_date": trade_date, "count": len(items)}
        result.update(self._sync_watchlist_alerts(trade_date))
        return result

    def _sync_watchlist_alerts(self, trade_date: Optional[str]) -> Dict[str, Any]:
        if not trade_date:
            return {"alerts_created": 0, "alerts_matched_users": 0}
        try:
            from services.watchlist_risk_alert_service import WatchlistRiskAlertService

            alert_result = WatchlistRiskAlertService().sync_alerts_for_trade_date(
                trade_date=trade_date
            )
            return {
                "alerts_created": alert_result.get("created", 0),
                "alerts_matched_users": alert_result.get("matched_users", 0),
                "emails_sent": alert_result.get("emails_sent", 0),
            }
        except Exception as exc:
            logger.warning(f"[RiskStockService] watchlist alert sync failed: {exc}")
            return {"alerts_created": 0, "alerts_matched_users": 0}

    def get_latest_trade_date(self) -> Optional[str]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(trade_date) AS trade_date FROM risk_stock_items")
            row = cursor.fetchone()
            return row.get("trade_date") if row else None

    def refresh_daily(self, trade_date: Optional[str] = None, source: str = "auto") -> Dict[str, Any]:
        effective_date, rows = self.collector.collect_rows(trade_date=trade_date)
        result = self.refresh_from_rows(effective_date, rows, source=source)
        result["source_rows"] = len(rows)
        result.update(self._sync_watchlist_alerts(result.get("trade_date")))
        logger.info(
            f"[RiskStockService] refreshed trade_date={result.get('trade_date')} "
            f"classified={result.get('count')} source_rows={len(rows)}"
        )
        return result

    def get_items(self, trade_date: Optional[str] = None, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if trade_date is None:
                cursor.execute("SELECT MAX(trade_date) AS trade_date FROM risk_stock_items")
                row = cursor.fetchone()
                trade_date = row.get("trade_date") if row else None
            if not trade_date:
                return []

            cursor.execute(
                """
                SELECT *
                FROM risk_stock_items
                WHERE trade_date = ?
                ORDER BY risk_level DESC, limit_up_days DESC, ts_code ASC
                """,
                (trade_date,),
            )
            rows = [dict(row) for row in cursor.fetchall()]

        if tag:
            rows = [row for row in rows if tag in self._parse_tags(row.get("tags_json"))]
        return rows

    def _classify_row(self, trade_date: str, row: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        ts_code = str(row.get("ts_code") or "").strip().upper()
        name = str(row.get("name") or "").strip()
        if not ts_code or not name:
            return None

        limit_up_days = int(row.get("limit_up_days") or 0)
        limit_down_days = int(row.get("limit_down_days") or 0)
        pct_chg = row.get("pct_chg")
        pools = [str(pool) for pool in (row.get("pools") or []) if pool]
        pool_reasons = [str(reason) for reason in (row.get("pool_reasons") or []) if reason]
        is_st = self._is_st_name(name)
        tags = []
        reasons = []

        if is_st:
            tags.append("ST股")
            reasons.append("股票名称包含 ST 风险标识")

        # 需求 1：连续 2 个交易日涨停/跌停 → 高风险
        if limit_up_days >= 2:
            tags.append("连续涨停")
            reasons.append(f"连续涨停 {limit_up_days} 天")
        if limit_up_days >= 3:
            tags.append("三连板")
            tags.append("高度板")
            if limit_up_days >= 4:
                tags.append("四连板+")

        if limit_down_days >= 2:
            tags.append("连续跌停")
            reasons.append(f"连续跌停 {limit_down_days} 天")

        # 需求 2/3/4：涨幅池 / 创业板大波动 / ST征兆（由 collector 计算，附带原因）
        for pool in pools:
            if pool not in tags:
                tags.append(pool)
        reasons.extend(pool_reasons)

        if not tags:
            return None

        if is_st and limit_up_days >= 3:
            tags.append("ST+连板")

        risk_level = self._resolve_risk_level(
            is_st=is_st,
            limit_up_days=limit_up_days,
            limit_down_days=limit_down_days,
            tags=tags,
        )
        return {
            "trade_date": trade_date,
            "ts_code": ts_code,
            "name": name,
            "market": row.get("market") or "",
            "tags": tags,
            "risk_level": risk_level,
            "reason": "；".join(reasons),
            "limit_up_days": limit_up_days,
            "limit_down_days": limit_down_days,
            "pct_chg": round(float(pct_chg), 2) if pct_chg is not None else None,
            "is_st": is_st,
            "source": source,
        }

    @staticmethod
    def _resolve_risk_level(
        is_st: bool,
        limit_up_days: int,
        limit_down_days: int,
        tags: List[str],
    ) -> str:
        # 高风险：ST 股 / 连续 2 日以上涨停或跌停
        if is_st or limit_up_days >= 2 or limit_down_days >= 2:
            return "high"
        # 中风险：9% 涨幅档 / 创业板大波动 / ST 征兆
        if any(tag in tags for tag in ("9%涨幅池", "创业板大波动", "ST征兆")):
            return "medium"
        # 低风险：仅 5% 涨幅档等观察性标签
        return "low"

    def _is_st_name(self, name: str) -> bool:
        normalized = name.upper().replace("＊", "*")
        return "ST" in normalized

    def _parse_tags(self, raw_tags: Any) -> List[str]:
        if not raw_tags:
            return []
        if isinstance(raw_tags, list):
            return raw_tags
        try:
            parsed = json.loads(raw_tags)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
