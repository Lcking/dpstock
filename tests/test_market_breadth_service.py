import pandas as pd

from services.market_breadth_service import MarketBreadthService
from services.market_overview_service import MarketOverviewService


def test_breadth_aggregates_up_down_and_limit(monkeypatch):
    service = MarketBreadthService()
    spot = pd.DataFrame(
        [
            {"代码": "600000", "涨跌幅": 10.0},  # 主板涨停
            {"代码": "600001", "涨跌幅": 1.2},
            {"代码": "600002", "涨跌幅": 0.0},
            {"代码": "600003", "涨跌幅": -2.0},
            {"代码": "300001", "涨跌幅": 20.0},  # 创业板涨停
            {"代码": "600004", "涨跌幅": -10.0},  # 主板跌停
        ]
    )

    class _FakeCollector:
        def fetch_spot_full_market(self, trade_date=None):
            return spot

    monkeypatch.setattr(
        "services.risk_stock_collector.RiskStockCollector",
        lambda: _FakeCollector(),
    )

    payload = service._build_breadth()
    assert payload["status"] == "ok"
    assert payload["up"] == 3
    assert payload["down"] == 2
    assert payload["flat"] == 1
    assert payload["limit_up"] == 2
    assert payload["limit_down"] == 1
    assert payload["total"] == 6
    assert payload["temperature"] == round(3 / 6 * 100, 1)
    assert "auction" in payload
    assert payload["auction"]["window"] == "09:15–09:25"


def test_full_spot_usable_requires_enough_rows():
    from services.risk_stock_collector import RiskStockCollector

    small = pd.DataFrame([{"代码": "600000", "名称": "x", "涨跌幅": 1.0}] * 100)
    large = pd.DataFrame([{"代码": f"{i:06d}", "名称": "x", "涨跌幅": 1.0} for i in range(2500)])
    assert RiskStockCollector._is_full_spot_usable(small) is False
    assert RiskStockCollector._is_full_spot_usable(large) is True


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

    monkeypatch.setattr(service, "_fetch_index", lambda spec: next(i for i in fake_items if i["key"] == spec.key))
    monkeypatch.setattr(service, "_safe_breadth", lambda: fake_breadth)
    service._cache = None
    service._cache_at = 0.0

    payload = service.get_overview()
    assert payload["breadth"]["status"] == "ok"
    assert payload["breadth"]["limit_up"] == 45
    brief = payload["auction_brief"]
    assert brief["phase"] == "regular"
    assert brief["active"] is False
    assert "上证高开" in brief["summary"]
    assert "沪深300低开" in brief["summary"]
    assert "涨停 45" in brief["summary"]
