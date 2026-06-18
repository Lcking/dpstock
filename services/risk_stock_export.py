"""
Export helpers for the daily risk stock list.
"""
from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List, Tuple

import pandas as pd

RISK_LEVEL_LABELS = {
    "high": "高风险",
    "medium": "中风险",
    "low": "低风险",
}

EXPORT_COLUMNS: List[Tuple[str, str]] = [
    ("trade_date", "交易日"),
    ("ts_code", "股票代码"),
    ("name", "股票名称"),
    ("market", "市场/行业"),
    ("tags", "风险标签"),
    ("limit_up_days", "连板天数"),
    ("risk_level", "风险等级"),
    ("reason", "原因"),
]


def _parse_tags(raw_tags: Any) -> List[str]:
    if isinstance(raw_tags, list):
        return raw_tags
    try:
        parsed = json.loads(raw_tags or "[]")
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def build_export_rows(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in items:
        tags = item.get("tags")
        if tags is None:
            tags = _parse_tags(item.get("tags_json"))
        risk_level = str(item.get("risk_level") or "")
        rows.append(
            {
                "trade_date": item.get("trade_date") or "",
                "ts_code": item.get("ts_code") or "",
                "name": item.get("name") or "",
                "market": item.get("market") or "",
                "tags": "、".join(tags),
                "limit_up_days": int(item.get("limit_up_days") or 0),
                "risk_level": RISK_LEVEL_LABELS.get(risk_level, risk_level),
                "reason": item.get("reason") or "",
            }
        )
    return rows


def build_export_filename(trade_date: str | None, tag: str | None, ext: str) -> str:
    safe_date = trade_date or "latest"
    if tag:
        safe_tag = tag.replace("/", "-").replace("+", "plus")
        return f"risk-stocks_{safe_date}_{safe_tag}.{ext}"
    return f"risk-stocks_{safe_date}.{ext}"


def render_csv_bytes(items: List[Dict[str, Any]]) -> bytes:
    rows = build_export_rows(items)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[column for _, column in EXPORT_COLUMNS],
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({label: row[key] for key, label in EXPORT_COLUMNS})
    return buffer.getvalue().encode("utf-8-sig")


def render_xlsx_bytes(items: List[Dict[str, Any]]) -> bytes:
    rows = build_export_rows(items)
    columns = [label for _, label in EXPORT_COLUMNS]
    if rows:
        data = [{label: row[key] for key, label in EXPORT_COLUMNS} for row in rows]
        frame = pd.DataFrame(data, columns=columns)
    else:
        frame = pd.DataFrame(columns=columns)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="风险股清单")
    return buffer.getvalue()
