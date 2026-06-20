#!/usr/bin/env python3
"""
Backfill missing stock_name for archived articles (especially ETF/LOF).
"""
from __future__ import annotations

import argparse
import asyncio

from database.db_factory import DatabaseFactory
from services.instrument_name_resolver import (
    fallback_display_name,
    preload_fund_name_caches,
    resolve_display_name,
)
from utils.logger import get_logger

logger = get_logger()


async def backfill_missing_names(dry_run: bool = False, use_fallback: bool = True) -> int:
    preload_fund_name_caches(force=True)

    updated = 0
    with DatabaseFactory.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, stock_code, stock_name, market_type, title
            FROM articles
            WHERE stock_name IS NULL OR TRIM(stock_name) = ''
            ORDER BY id
            """
        )
        rows = cursor.fetchall()

    for row in rows:
        article = dict(row)
        code = str(article.get("stock_code") or "")
        market_type = str(article.get("market_type") or "A")
        resolved = resolve_display_name(
            code,
            market_type=market_type,
            stock_name=str(article.get("stock_name") or ""),
            allow_network=True,
        )
        if not resolved and use_fallback:
            resolved = fallback_display_name(code, market_type)
            logger.warning(
                f"article {article['id']}: fallback name for {code} -> {resolved}"
            )
        if not resolved:
            logger.warning(f"skip article {article['id']}: unable to resolve name for {code}")
            continue

        new_title = str(article.get("title") or "")
        if code and resolved and resolved not in new_title:
            new_title = new_title.replace(f" {code} ", f" {resolved} {code} ", 1)
            if new_title == str(article.get("title") or ""):
                new_title = new_title.replace(f"{code} ", f"{resolved} {code} ", 1)

        logger.info(f"article {article['id']}: {code} -> {resolved}")
        if dry_run:
            updated += 1
            continue

        with DatabaseFactory.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE articles
                SET stock_name = ?, title = ?
                WHERE id = ?
                """,
                (resolved, new_title, article["id"]),
            )
            conn.commit()
        updated += 1

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill missing archived article stock names")
    parser.add_argument("--dry-run", action="store_true", help="Only log changes without writing")
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Skip rows that cannot be resolved to a real name",
    )
    args = parser.parse_args()
    count = asyncio.run(
        backfill_missing_names(dry_run=args.dry_run, use_fallback=not args.no_fallback)
    )
    print(f"processed {count} articles")


if __name__ == "__main__":
    main()
