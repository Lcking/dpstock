import argparse
import asyncio
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.ai_score.calculator import AiScoreCalculator
from services.stock_data_provider import StockDataProvider
from services.technical_indicator import TechnicalIndicator
from utils.logger import get_logger


logger = get_logger()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="为缺失 ai_score_json 的文章回填基础版 AI 综合评分。"
    )
    parser.add_argument(
        "--db-path",
        default="data/stocks.db",
        help="SQLite 数据库路径，默认 data/stocks.db",
    )
    parser.add_argument(
        "--article-ids",
        nargs="*",
        type=int,
        help="指定要回填的文章 ID；不传则回填最近缺失的文章",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="未指定文章 ID 时，最多处理多少篇缺失文章",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将处理哪些文章，不写入数据库",
    )
    return parser.parse_args()


def load_candidates(
    conn: sqlite3.Connection,
    article_ids: Optional[List[int]],
    limit: int,
) -> List[sqlite3.Row]:
    if article_ids:
        placeholders = ",".join("?" for _ in article_ids)
        sql = f"""
            SELECT id, title, stock_code, stock_name, market_type, content, score, legacy_score, score_version, publish_date
            FROM articles
            WHERE id IN ({placeholders})
            ORDER BY publish_date DESC, id DESC
        """
        return conn.execute(sql, tuple(article_ids)).fetchall()

    sql = """
        SELECT id, title, stock_code, stock_name, market_type, content, score, legacy_score, score_version, publish_date
        FROM articles
        WHERE ai_score_json IS NULL
          AND content LIKE '{%'
        ORDER BY publish_date DESC, id DESC
        LIMIT ?
    """
    return conn.execute(sql, (limit,)).fetchall()


def parse_analysis_v1(content: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(content)
    except Exception:
        return None

    if not isinstance(parsed, dict):
        return None

    required_fields = {
        "structure_snapshot",
        "pattern_fitting",
        "indicator_translate",
        "risk_of_misreading",
        "judgment_zone",
    }
    if not required_fields.issubset(parsed.keys()):
        return None
    return parsed


async def build_ai_score_payload(
    provider: StockDataProvider,
    indicator: TechnicalIndicator,
    calculator: AiScoreCalculator,
    article: sqlite3.Row,
) -> Optional[Dict[str, Any]]:
    analysis_v1 = parse_analysis_v1(article["content"])
    if analysis_v1 is None:
        logger.warning(f"[BackfillAiScore] 跳过文章 {article['id']}：正文不是 Analysis V1 JSON")
        return None

    publish_date = str(article["publish_date"] or "").strip()
    if not publish_date:
        logger.warning(f"[BackfillAiScore] 跳过文章 {article['id']}：缺少 publish_date")
        return None

    end_date = publish_date.replace("-", "")
    df = await provider.get_stock_data(
        stock_code=article["stock_code"],
        market_type=article["market_type"],
        end_date=end_date,
    )
    if getattr(df, "empty", True):
        logger.warning(f"[BackfillAiScore] 跳过文章 {article['id']}：历史行情为空")
        return None
    if hasattr(df, "error"):
        logger.warning(f"[BackfillAiScore] 跳过文章 {article['id']}：{df.error}")
        return None

    publish_cutoff = pd.Timestamp(publish_date)
    df = df.loc[df.index <= publish_cutoff]
    if df.empty:
        logger.warning(f"[BackfillAiScore] 跳过文章 {article['id']}：发布日期之前无可用行情")
        return None

    df_with_indicators = indicator.calculate_indicators(df)
    ai_score_obj = calculator.calculate(
        df=df_with_indicators,
        stock_code=article["stock_code"],
        market_type=article["market_type"],
        analysis_v1=analysis_v1,
        include_enhancements=False,
    )
    ai_score = ai_score_obj.model_dump() if hasattr(ai_score_obj, "model_dump") else ai_score_obj
    if not isinstance(ai_score, dict):
        logger.warning(f"[BackfillAiScore] 跳过文章 {article['id']}：AI 评分结果无效")
        return None

    analysis_v1["ai_score"] = ai_score
    overall_score = int(ai_score.get("overall", {}).get("score", article["score"] or 0))
    legacy_score = article["legacy_score"] if article["legacy_score"] is not None else article["score"]
    return {
        "content": json.dumps(analysis_v1, ensure_ascii=False),
        "score": overall_score,
        "legacy_score": legacy_score,
        "score_version": str(ai_score.get("version", "1.0.0")),
        "ai_score_json": json.dumps(ai_score, ensure_ascii=False),
    }


async def main() -> int:
    args = parse_args()
    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        candidates = load_candidates(conn, args.article_ids, args.limit)
        if not candidates:
            print("没有需要回填的文章。")
            return 0

        provider = StockDataProvider()
        indicator = TechnicalIndicator()
        calculator = AiScoreCalculator()

        updated = 0
        for article in candidates:
            print(
                f"处理文章 {article['id']}: {article['publish_date']} {article['stock_name']} {article['stock_code']}"
            )
            payload = await build_ai_score_payload(provider, indicator, calculator, article)
            if payload is None:
                continue

            if args.dry_run:
                print(f"  dry-run: 将回填 score={payload['score']} version={payload['score_version']}")
                updated += 1
                continue

            conn.execute(
                """
                UPDATE articles
                SET content = ?,
                    score = ?,
                    legacy_score = ?,
                    score_version = ?,
                    ai_score_json = ?
                WHERE id = ?
                """,
                (
                    payload["content"],
                    payload["score"],
                    payload["legacy_score"],
                    payload["score_version"],
                    payload["ai_score_json"],
                    article["id"],
                ),
            )
            conn.commit()
            updated += 1
            print(f"  已回填 score={payload['score']} version={payload['score_version']}")

        print(f"完成，共处理 {len(candidates)} 篇，成功回填 {updated} 篇。")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
