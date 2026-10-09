import time

import pandas as pd

from services.market_breadth_service import MarketBreadthService, format_market_breadth_note
from services.market_overview_service import MarketOverviewService


def test_breadth_prefers_fast_ulist_path(monkeypatch):
    service = MarketBreadthService()
    monkeypatch.setattr(
        service,
        "_fetch_breadth_fast",
        lambda: {"up": 3200, "down": 1500, "flat": 200, "limit_up": 66, "limit_down": 1},
    )

    def _should_not_call():
        raise AssertionError("spot fallback should not run when fast path works")

    monkeypatch.setattr(service, "_fetch_breadth_from_spot", _should_not_call)

    payload = service._build_breadth()
    assert payload["status"] == "ok"
    assert payload["source"] == "eastmoney_ulist"
    assert payload["up"] == 3200
    assert payload["down"] == 1500
    assert payload["flat"] == 200
    assert payload["limit_up"] == 66
    assert payload["limit_down"] == 1
    assert payload["total"] == 4900
    assert payload["temperature"] == round(3200 / 4900 * 100, 1)
    assert "auction" in payload


def test_breadth_falls_back_to_spot(monkeypatch):
    service = MarketBreadthService()
    spot = pd.DataFrame(
        [
            {"代码": "600000", "涨跌幅": 10.0},
            {"代码": "600001", "涨跌幅": 1.2},
            {"代码": "600002", "涨跌幅": 0.0},
            {"代码": "600003", "涨跌幅": -2.0},
            {"代码": "300001", "涨跌幅": 20.0},
            {"代码": "600004", "涨跌幅": -10.0},
        ]
    )

    class _FakeCollector:
        def fetch_spot_full_market(self, trade_date=None):
            return spot

    monkeypatch.setattr(service, "_fetch_breadth_fast", lambda: None)
    monkeypatch.setattr(
        "services.risk_stock_collector.RiskStockCollector",
        lambda: _FakeCollector(),
    )

    payload = service._build_breadth()
    assert payload["status"] == "ok"
    assert payload["source"] == "spot"
    assert payload["up"] == 3
    assert payload["down"] == 2
    assert payload["flat"] == 1
    assert payload["limit_up"] == 2
    assert payload["limit_down"] == 1


def test_full_spot_usable_requires_enough_rows():
    from services.risk_stock_collector import RiskStockCollector

    small = pd.DataFrame([{"代码": "600000", "名称": "x", "涨跌幅": 1.0}] * 100)
    large = pd.DataFrame(
        [{"代码": f"{i:06d}", "名称": "x", "涨跌幅": 1.0} for i in range(2500)]
    )
    assert RiskStockCollector._is_full_spot_usable(small) is False
    assert RiskStockCollector._is_full_spot_usable(large) is True


def test_format_market_breadth_note():
    note = format_market_breadth_note(
        {
            "status": "ok",
            "temperature_label": "偏强",
            "temperature": 65.4,
            "up": 3448,
            "down": 1657,
            "flat": 170,
            "limit_up": 66,
            "limit_down": 0,
        }
    )
    assert "偏强" in note
    assert "65.4°" in note
    assert "上涨 3448 家" in note
    assert "涨停 66" in note
    assert "不构成对该股方向的判断" in note
    assert format_market_breadth_note({"status": "unavailable"}) == ""
    assert format_market_breadth_note(None) == ""


def test_temperature_label_rules():
    assert MarketBreadthService._temperature_label(70, limit_up=90, limit_down=5) == "偏热"
    assert MarketBreadthService._temperature_label(30, limit_up=5, limit_down=50) == "偏冷"
    assert MarketBreadthService._temperature_label(65, limit_up=10, limit_down=5) == "偏强"
    assert MarketBreadthService._temperature_label(35, limit_up=5, limit_down=5) == "偏弱"
    assert MarketBreadthService._temperature_label(50, limit_up=10, limit_down=5) == "中性"


def test_overview_attaches_breadth_and_auction_brief(monkeypatch):
    service = MarketOverviewService()
    fake_items = [
        {
            "key": "shanghai",
            "name": "上证指数",
            "status": "ok",
            "change_percent": 0.42,
        },
        {
            "key": "csi300",
            "name": "沪深300",
            "status": "ok",
            "change_percent": -0.21,
        },
        {"key": "hangseng", "status": "unavailable"},
        {"key": "nasdaq", "status": "unavailable"},
    ]
    fake_breadth = {
        "status": "ok",
        "up": 2200,
        "down": 1800,
        "flat": 200,
        "limit_up": 45,
        "limit_down": 12,
        "temperature": 52.4,
        "temperature_label": "中性",
        "auction": {
            "phase": "regular",
            "active": False,
            "hint": "已开盘；竞价简报仅作开盘参考",
            "window": "09:15–09:25",
        },
    }

    monkeypatch.setattr(
        service, "_fetch_index", lambda spec: next(i for i in fake_items if i["key"] == spec.key)
    )
    monkeypatch.setattr(service, "_breadth_for_overview", lambda: fake_breadth)
    service._items_cache = None
    service._items_cache_at = 0.0

    payload = service.get_overview()
    assert payload["breadth"]["status"] == "ok"
    assert payload["breadth"]["limit_up"] == 45
    brief = payload["auction_brief"]
    assert brief["phase"] == "regular"
    assert brief["active"] is False
    assert "上证高开" in brief["summary"]
    assert "沪深300低开" in brief["summary"]
    assert "涨停 45" in brief["summary"]


def test_prompt_breadth_skips_spot_and_does_not_cache_failure(monkeypatch):
    service = MarketBreadthService()
    service._cache = None
    seen = {}

    def fast(**kwargs):
        seen.update(kwargs)
        return None

    def spot():
        raise AssertionError("诊股不能走全市场回退")

    monkeypatch.setattr(service, "_fetch_breadth_fast", fast)
    monkeypatch.setattr(service, "_fetch_breadth_from_spot", spot)

    payload = service.get_breadth_for_prompt()
    assert payload["status"] == "unavailable"
    assert seen.get("request_timeout") == service.PROMPT_FAST_TIMEOUT_SECONDS
    assert service._cache is None


def test_prompt_reuses_recent_success_without_fetch(monkeypatch):
    service = MarketBreadthService()
    service._cache = {
        "status": "ok",
        "temperature": 61.2,
        "temperature_label": "偏强",
        "up": 3000,
        "down": 1500,
        "flat": 100,
        "limit_up": 10,
        "limit_down": 1,
    }
    service._cache_at = time.time() - (service.INTRADAY_CACHE_TTL_SECONDS + 30)

    def boom(*args, **kwargs):
        raise AssertionError("近期成功的温度应直接复用")

    monkeypatch.setattr(service, "_fetch_breadth_fast", boom)
    monkeypatch.setattr(service, "_fetch_breadth_from_spot", boom)

    payload = service.get_breadth_for_prompt()
    assert payload["temperature"] == 61.2


def test_overview_does_not_wait_on_breadth_fetch(monkeypatch):
    service = MarketOverviewService()

    def boom():
        raise AssertionError("首页指数接口不能去拉温度")

    monkeypatch.setattr(
        "services.market_breadth_service.market_breadth_service.get_breadth",
        boom,
    )
    monkeypatch.setattr(
        "services.market_breadth_service.market_breadth_service.peek_fresh",
        lambda: None,
    )
    monkeypatch.setattr(
        service,
        "_fetch_index",
        lambda spec: {
            "key": spec.key,
            "name": spec.name,
            "status": "ok",
            "change_percent": 0.42 if spec.key == "shanghai" else -0.2,
        },
    )

    payload = service.get_overview()
    assert len(payload["items"]) == 4
    assert payload["breadth"] is None
    assert "上证高开" in payload["auction_brief"]["summary"]
    assert "涨停" not in payload["auction_brief"]["summary"]
