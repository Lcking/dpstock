import json
import sys
import types

import pandas as pd
import pytest

from services.ai_analyzer import AIAnalyzer, _extract_stream_delta


@pytest.fixture(autouse=True)
def _stub_scipy(monkeypatch):
    """本机 scipy 扩展在当前解释器下无法加载，统计分位用纯函数替上。"""
    stats_mod = types.ModuleType("scipy.stats")
    stats_mod.percentileofscore = lambda values, score: 50.0
    scipy_mod = types.ModuleType("scipy")
    scipy_mod.stats = stats_mod
    monkeypatch.setitem(sys.modules, "scipy", scipy_mod)
    monkeypatch.setitem(sys.modules, "scipy.stats", stats_mod)


def _mini_df():
    return pd.DataFrame(
        {
            "Open": [10.0] * 40,
            "High": [10.5] * 40,
            "Low": [9.5] * 40,
            "Close": [10.0 + i * 0.01 for i in range(40)],
            "Volume": [1_000_000] * 40,
            "MA5": [10.0] * 40,
            "MA20": [10.0] * 40,
            "MA60": [10.0] * 40,
            "MA200": [10.0] * 40,
            "RSI": [50.0] * 40,
            "MACD": [0.1] * 40,
            "MACD_Signal": [0.05] * 40,
            "Signal": [0.05] * 40,
            "Histogram": [0.05] * 40,
            "Volume_MA20": [900_000] * 40,
            "Volume_Ratio": [1.1] * 40,
            "Volatility": [2.5] * 40,
            "Change": [0.1] * 40,
        }
    )


@pytest.mark.asyncio
async def test_a_share_prompt_includes_market_breadth_note(monkeypatch):
    analyzer = AIAnalyzer()
    captured = {}

    monkeypatch.setattr(
        "services.market_breadth_service.market_breadth_service.get_breadth_for_prompt",
        lambda: {
            "status": "ok",
            "temperature_label": "偏强",
            "temperature": 65.4,
            "up": 3448,
            "down": 1657,
            "flat": 170,
            "limit_up": 66,
            "limit_down": 0,
        },
    )

    from services import ai_analyzer as mod

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"stock_code":"600000","stock_name":"测试","market_type":"A",'
                                '"analysis_date":"2026-08-04",'
                                '"structure_snapshot":{"structure_type":"consolidation",'
                                '"ma200_position":"near","phase":"unclear","description":"x"},'
                                '"pattern_analysis":{"pattern_type":"none","description":"x","key_levels":[]},'
                                '"indicator_translation":[],"misread_risks":[],'
                                '"judgment_zone":{"candidates":[],"risk_checks":[]}}'
                            )
                        }
                    }
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None, headers=None, timeout=None):
            captured["messages"] = (json or {}).get("messages") or []
            return FakeResponse()

    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda *a, **k: FakeClient())
    monkeypatch.setattr(analyzer, "API_KEY", "test-key", raising=False)
    monkeypatch.setattr(analyzer, "API_URL", "https://example.com/v1", raising=False)
    monkeypatch.setattr(analyzer, "API_MODEL", "test-model", raising=False)
    monkeypatch.setattr(analyzer, "API_TIMEOUT", 30, raising=False)

    async for _ in analyzer.get_ai_analysis(
        _mini_df(), "600000", stock_name="测试银行", market_type="A", stream=False
    ):
        pass

    prompt_text = "\n".join(
        str(m.get("content") or "")
        for m in captured.get("messages") or []
        if isinstance(m, dict)
    )
    assert captured.get("messages"), "expected LLM request to be captured"
    assert "市场广度" in prompt_text
    assert "偏强" in prompt_text
    assert "上涨 3448 家" in prompt_text


@pytest.mark.asyncio
async def test_hk_prompt_skips_market_breadth_note(monkeypatch):
    analyzer = AIAnalyzer()
    captured = {}
    called = {"breadth": False}

    def boom():
        called["breadth"] = True
        raise AssertionError("HK should not fetch A-share breadth")

    monkeypatch.setattr(
        "services.market_breadth_service.market_breadth_service.get_breadth_for_prompt",
        boom,
    )

    from services import ai_analyzer as mod

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"stock_code":"00700","stock_name":"腾讯","market_type":"HK",'
                                '"analysis_date":"2026-08-04",'
                                '"structure_snapshot":{"structure_type":"consolidation",'
                                '"ma200_position":"near","phase":"unclear","description":"x"},'
                                '"pattern_analysis":{"pattern_type":"none","description":"x","key_levels":[]},'
                                '"indicator_translation":[],"misread_risks":[],'
                                '"judgment_zone":{"candidates":[],"risk_checks":[]}}'
                            )
                        }
                    }
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None, headers=None, timeout=None):
            captured["messages"] = (json or {}).get("messages") or []
            return FakeResponse()

    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda *a, **k: FakeClient())
    monkeypatch.setattr(analyzer, "API_KEY", "test-key", raising=False)
    monkeypatch.setattr(analyzer, "API_URL", "https://example.com/v1", raising=False)
    monkeypatch.setattr(analyzer, "API_MODEL", "test-model", raising=False)
    monkeypatch.setattr(analyzer, "API_TIMEOUT", 30, raising=False)

    async for _ in analyzer.get_ai_analysis(
        _mini_df(), "00700", stock_name="腾讯", market_type="HK", stream=False
    ):
        pass

    assert called["breadth"] is False
    prompt_text = "\n".join(
        str(m.get("content") or "")
        for m in captured.get("messages") or []
        if isinstance(m, dict)
    )
    assert captured.get("messages"), "expected LLM request to be captured"
    assert "当日市场广度" not in prompt_text


def test_extract_stream_delta_keeps_reasoning_out_of_content():
    assert _extract_stream_delta(
        {"choices": [{"delta": {"reasoning_content": "先看均线"}}]}
    ) == ("reasoning", "先看均线")
    assert _extract_stream_delta(
        {"choices": [{"delta": {"content": "正文"}}]}
    ) == ("content", "正文")
    assert _extract_stream_delta(
        {"choices": [{"delta": {"content": "正文", "reasoning_content": "先看均线"}}]}
    ) == ("content", "正文")
    assert _extract_stream_delta(
        {"choices": [{"finish_reason": "stop", "delta": {}}]}
    ) == ("stop", "")
    assert _extract_stream_delta({"choices": [{"delta": {"content": ""}}]}) == ("ignore", "")


@pytest.mark.asyncio
async def test_stream_reasoning_is_progress_not_analysis(monkeypatch):
    analyzer = AIAnalyzer()
    monkeypatch.setattr(
        "services.market_breadth_service.market_breadth_service.get_breadth_for_prompt",
        lambda: {"status": "unavailable"},
    )

    async def _no_score(*args, **kwargs):
        return None

    monkeypatch.setattr(analyzer, "_calculate_ai_score_with_timeout", _no_score)

    from services import ai_analyzer as mod

    class FakeStream:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def aiter_text(self):
            lines = [
                {"choices": [{"delta": {"reasoning_content": "内部推理甲"}}]},
                {"choices": [{"delta": {"reasoning_content": "内部推理乙"}}]},
                {"choices": [{"delta": {"content": "可见正文"}}]},
            ]
            for item in lines:
                yield "data: " + json.dumps(item, ensure_ascii=False) + "\n"
            yield "data: [DONE]\n"

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def stream(self, *args, **kwargs):
            return FakeStream()

    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda *a, **k: FakeClient())
    monkeypatch.setattr(analyzer, "API_KEY", "test-key", raising=False)
    monkeypatch.setattr(analyzer, "API_URL", "https://example.com/v1", raising=False)
    monkeypatch.setattr(analyzer, "API_MODEL", "test-model", raising=False)
    monkeypatch.setattr(analyzer, "API_TIMEOUT", 30, raising=False)

    chunks = []
    async for raw in analyzer.get_ai_analysis(
        _mini_df(), "600000", stock_name="测试银行", market_type="A", stream=True
    ):
        chunks.append(json.loads(raw))

    reasoning = [item for item in chunks if item.get("event") == "reasoning"]
    contents = [
        item.get("ai_analysis_chunk")
        for item in chunks
        if item.get("ai_analysis_chunk")
    ]
    assert len(reasoning) == 1
    assert reasoning[0]["status"] == "analyzing"
    assert "reasoning_content" not in reasoning[0]
    assert any("可见正文" in (text or "") for text in contents)
    blob = json.dumps(chunks, ensure_ascii=False)
    assert "内部推理甲" not in blob
    assert "内部推理乙" not in blob
