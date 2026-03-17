import json

import pandas as pd
import pytest

from services.stock_analyzer_service import (
    StockAnalyzerService,
    _augment_analysis_v1_with_turnover,
    _build_turnover_profile,
)
from services.stock_data_provider import StockDataProvider


def test_enrich_a_share_turnover_uses_daily_basic_when_missing(monkeypatch):
    provider = StockDataProvider()

    daily_df = pd.DataFrame(
        {
            "日期": ["20260102", "20260103"],
            "股票代码": ["000001", "000001"],
            "开盘": [10.0, 10.2],
            "收盘": [10.1, 10.4],
            "最高": [10.2, 10.5],
            "最低": [9.9, 10.1],
            "成交量": [100000, 120000],
            "成交额": [1000000, 1200000],
            "振幅": [2.0, 3.0],
            "涨跌幅": [1.0, 2.97],
            "涨跌额": [0.1, 0.3],
            "换手率": [None, None],
        }
    )

    basic_df = pd.DataFrame(
        {
            "trade_date": ["20260103", "20260102"],
            "turnover_rate": [4.2, 3.8],
        }
    )

    class _DummyClient:
        is_available = True

        @staticmethod
        def get_daily_basic(ts_code: str, trade_date: str = None):
            return basic_df

    monkeypatch.setattr("services.stock_data_provider.tushare_client", _DummyClient())

    out = provider._enrich_a_share_turnover(
        daily_df.copy(),
        stock_code="000001",
        start_date="20260101",
        end_date="20260104",
    )

    assert out["换手率"].tolist() == [3.8, 4.2]


def test_enrich_a_share_turnover_clears_placeholder_zero_when_unavailable(monkeypatch):
    provider = StockDataProvider()

    daily_df = pd.DataFrame(
        {
            "日期": ["20260102"],
            "股票代码": ["000001"],
            "开盘": [10.0],
            "收盘": [10.1],
            "最高": [10.2],
            "最低": [9.9],
            "成交量": [100000],
            "成交额": [1000000],
            "振幅": [2.0],
            "涨跌幅": [1.0],
            "涨跌额": [0.1],
            "换手率": [0.0],
        }
    )

    class _DummyClient:
        is_available = False

    monkeypatch.setattr("services.stock_data_provider.tushare_client", _DummyClient())

    out = provider._enrich_a_share_turnover(
        daily_df.copy(),
        stock_code="000001",
        start_date="20260101",
        end_date="20260104",
        placeholder_zero=True,
    )

    assert pd.isna(out.iloc[0]["换手率"])


def test_build_turnover_profile_returns_expected_levels():
    low = _build_turnover_profile(0.8)
    mid = _build_turnover_profile(2.6)
    high = _build_turnover_profile(6.4)

    assert low["tag"] == "低活跃"
    assert mid["tag"] == "正常活跃"
    assert high["tag"] == "高活跃"
    assert "换手率" in high["interpretation"]


def test_augment_analysis_v1_with_turnover_injects_indicator_when_missing():
    analysis_v1 = {
        "indicator_translate": {
            "indicators": [
                {
                    "name": "RSI(14)",
                    "value": "52.1",
                    "signal": "neutral",
                    "interpretation": "RSI 在中性区域",
                }
            ],
            "global_note": "原有说明",
        }
    }

    out = _augment_analysis_v1_with_turnover(analysis_v1, 4.2)

    turnover_items = [item for item in out["indicator_translate"]["indicators"] if item["name"] == "换手率"]
    assert len(turnover_items) == 1
    assert turnover_items[0]["value"] == "4.20%"
    assert turnover_items[0]["signal"] == "strengthening"


@pytest.mark.asyncio
async def test_analyze_stock_emits_turnover_payload_and_report_indicator():
    service = StockAnalyzerService()

    class _DummyProvider:
        def resolve_stock_code(self, stock_code: str):
            return stock_code, "平安银行"

        async def get_stock_data(self, stock_code: str, market_type: str):
            return pd.DataFrame(
                {
                    "Close": [10.0, 10.3],
                    "Open": [9.9, 10.1],
                    "High": [10.2, 10.4],
                    "Low": [9.8, 10.0],
                    "Volume": [100000, 120000],
                    "Amount": [1000000, 1240000],
                    "Change_pct": [0.5, 3.0],
                    "Turnover": [3.8, 4.2],
                }
            )

        def lookup_stock_name(self, stock_code: str):
            return "平安银行"

    class _DummyIndicator:
        def calculate_indicators(self, df: pd.DataFrame):
            out = df.copy()
            out["RSI"] = [48.0, 52.0]
            out["MA5"] = [10.0, 10.1]
            out["MA20"] = [9.9, 10.0]
            out["MA60"] = [9.8, 9.9]
            out["MACD"] = [0.1, 0.2]
            out["Signal"] = [0.05, 0.1]
            out["Volume_MA"] = [100000, 100000]
            return out

    class _DummyScorer:
        def calculate_score(self, df: pd.DataFrame):
            return 88

        def get_recommendation(self, score: int):
            return "观察"

    class _DummyAIAnalyzer:
        async def get_ai_analysis(self, df, stock_code, stock_name, market_type, stream):
            yield json.dumps(
                {
                    "stock_code": stock_code,
                    "analysis_v1": {
                        "indicator_translate": {
                            "indicators": [
                                {
                                    "name": "RSI(14)",
                                    "value": "52.0",
                                    "signal": "neutral",
                                    "interpretation": "RSI 中性",
                                }
                            ],
                            "global_note": "原始说明",
                        }
                    },
                    "analysis": "测试报告",
                    "status": "completed",
                    "score": 88,
                    "recommendation": "观察",
                    "ai_score": None,
                }
            )

    class _DummyArchiveService:
        async def save_article(self, article_data):
            return None

    service.data_provider = _DummyProvider()
    service.indicator = _DummyIndicator()
    service.scorer = _DummyScorer()
    service.ai_analyzer = _DummyAIAnalyzer()
    service.archive_service = _DummyArchiveService()

    chunks = []
    async for chunk in service.analyze_stock("000001", market_type="A", stream=False):
        chunks.append(json.loads(chunk))

    assert chunks[0]["turnover_rate"] == 4.2
    assert chunks[0]["turnover_profile"]["tag"] == "高活跃"

    turnover_items = [
        item
        for item in chunks[-1]["analysis_v1"]["indicator_translate"]["indicators"]
        if item["name"] == "换手率"
    ]
    assert len(turnover_items) == 1
    assert chunks[-1]["turnover_profile"]["tag"] == "高活跃"


@pytest.mark.asyncio
async def test_analyze_stock_archives_augmented_analysis_v1_content():
    service = StockAnalyzerService()

    class _DummyProvider:
        def resolve_stock_code(self, stock_code: str):
            return stock_code, "平安银行"

        async def get_stock_data(self, stock_code: str, market_type: str):
            return pd.DataFrame(
                {
                    "Close": [10.0, 10.3],
                    "Open": [9.9, 10.1],
                    "High": [10.2, 10.4],
                    "Low": [9.8, 10.0],
                    "Volume": [100000, 120000],
                    "Amount": [1000000, 1240000],
                    "Change_pct": [0.5, 3.0],
                    "Turnover": [3.8, 4.2],
                }
            )

        def lookup_stock_name(self, stock_code: str):
            return "平安银行"

    class _DummyIndicator:
        def calculate_indicators(self, df: pd.DataFrame):
            out = df.copy()
            out["RSI"] = [48.0, 52.0]
            out["MA5"] = [10.0, 10.1]
            out["MA20"] = [9.9, 10.0]
            out["MA60"] = [9.8, 9.9]
            out["MACD"] = [0.1, 0.2]
            out["Signal"] = [0.05, 0.1]
            out["Volume_MA"] = [100000, 100000]
            return out

    class _DummyScorer:
        def calculate_score(self, df: pd.DataFrame):
            return 88

        def get_recommendation(self, score: int):
            return "观察"

    class _DummyAIAnalyzer:
        async def get_ai_analysis(self, df, stock_code, stock_name, market_type, stream):
            yield json.dumps(
                {
                    "stock_code": stock_code,
                    "analysis_v1": {
                        "stock_code": stock_code,
                        "stock_name": stock_name,
                        "market_type": market_type,
                        "analysis_date": "2026-03-09T00:00:00",
                        "structure_snapshot": {
                            "structure_type": "consolidation",
                            "ma200_position": "above",
                            "phase": "middle",
                            "key_levels": [],
                            "trend_description": "测试结构",
                        },
                        "pattern_fitting": {
                            "pattern_type": "none",
                            "pattern_description": "测试形态",
                            "completion_rate": 50,
                        },
                        "indicator_translate": {
                            "indicators": [
                                {
                                    "name": "RSI(14)",
                                    "value": "52.0",
                                    "signal": "neutral",
                                    "interpretation": "RSI 中性",
                                }
                            ],
                            "global_note": "原始说明",
                        },
                        "risk_of_misreading": {
                            "risk_level": "low",
                            "risk_factors": [],
                            "risk_flags": [],
                            "caution_note": "测试注意事项",
                        },
                        "judgment_zone": {
                            "candidates": [
                                {
                                    "option_id": "A",
                                    "option_type": "structure_premise",
                                    "description": "测试候选",
                                },
                                {
                                    "option_id": "B",
                                    "option_type": "structure_premise",
                                    "description": "测试候选2",
                                },
                            ],
                            "risk_checks": [],
                            "note": "测试备注",
                        },
                    },
                    "analysis": "```json\n{\"old\": \"content\"}\n```",
                    "status": "completed",
                    "score": 88,
                    "recommendation": "观察",
                    "ai_score": None,
                }
            )

    saved_articles = []

    class _DummyArchiveService:
        async def save_article(self, article_data):
            saved_articles.append(article_data)
            return 1

    service.data_provider = _DummyProvider()
    service.indicator = _DummyIndicator()
    service.scorer = _DummyScorer()
    service.ai_analyzer = _DummyAIAnalyzer()
    service.archive_service = _DummyArchiveService()

    async for _ in service.analyze_stock("000001", market_type="A", stream=False):
        pass

    assert len(saved_articles) == 1
    archived_content = json.loads(saved_articles[0]["content"])
    turnover_items = [
        item
        for item in archived_content["indicator_translate"]["indicators"]
        if item["name"] == "换手率"
    ]
    assert len(turnover_items) == 1
    assert turnover_items[0]["value"] == "4.20%"


@pytest.mark.asyncio
async def test_analyze_stock_archive_title_keeps_stock_name():
    service = StockAnalyzerService()

    class _DummyProvider:
        def resolve_stock_code(self, stock_code: str):
            return stock_code, ""

        async def get_stock_data(self, stock_code: str, market_type: str):
            return pd.DataFrame(
                {
                    "Close": [10.0, 10.3],
                    "Open": [9.9, 10.1],
                    "High": [10.2, 10.4],
                    "Low": [9.8, 10.0],
                    "Volume": [100000, 120000],
                    "Amount": [1000000, 1240000],
                    "Change_pct": [0.5, 3.0],
                    "Turnover": [3.8, 4.2],
                }
            )

        def lookup_stock_name(self, stock_code: str, allow_network: bool = False):
            return "贵州茅台"

    class _DummyIndicator:
        def calculate_indicators(self, df: pd.DataFrame):
            out = df.copy()
            out["RSI"] = [48.0, 52.0]
            out["MA5"] = [10.0, 10.1]
            out["MA20"] = [9.9, 10.0]
            out["MA60"] = [9.8, 9.9]
            out["MACD"] = [0.1, 0.2]
            out["Signal"] = [0.05, 0.1]
            out["Volume_MA"] = [100000, 100000]
            return out

    class _DummyScorer:
        def calculate_score(self, df: pd.DataFrame):
            return 88

        def get_recommendation(self, score: int):
            return "观察"

    class _DummyAIAnalyzer:
        async def get_ai_analysis(self, df, stock_code, stock_name, market_type, stream):
            yield json.dumps(
                {
                    "stock_code": stock_code,
                    "analysis": "测试报告",
                    "status": "completed",
                    "score": 88,
                    "recommendation": "观察",
                    "ai_score": None,
                }
            )

    saved_articles = []

    class _DummyArchiveService:
        async def save_article(self, article_data):
            saved_articles.append(article_data)
            return 1

    service.data_provider = _DummyProvider()
    service.indicator = _DummyIndicator()
    service.scorer = _DummyScorer()
    service.ai_analyzer = _DummyAIAnalyzer()
    service.archive_service = _DummyArchiveService()

    async for _ in service.analyze_stock("600519", market_type="A", stream=False):
        pass

    assert len(saved_articles) == 1
    assert "贵州茅台 600519 股票行情走势异动分析" in saved_articles[0]["title"]
