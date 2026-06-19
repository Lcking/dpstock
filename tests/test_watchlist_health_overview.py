from services.trend.schemas import TrendResult
from services.watchlist.service import WatchlistService
from schemas.watchlist import (
    CapitalFlowSummary,
    EventSummary,
    JudgementSummary,
    RelativeStrengthSummary,
    RiskSummary,
    WatchlistItemSummary,
)


def _item(
    ts_code: str,
    trend: str,
    strength: int,
    rs: str | None,
    risk: str,
    judgement: bool = False,
):
    return WatchlistItemSummary(
        ts_code=ts_code,
        name=ts_code,
        asof="2026-06-18",
        price=10.0,
        change_pct=None,
        trend=TrendResult(direction=trend, strength=strength, degraded=False, evidence=[]),
        relative_strength=RelativeStrengthSummary(label_20d=rs),
        capital_flow=CapitalFlowSummary(label="中性", available=True, degraded=False),
        risk=RiskSummary(level=risk),
        events=EventSummary(flag="none", available=True),
        judgement=JudgementSummary(has_active=judgement, candidate="A" if judgement else None),
    )


def test_watchlist_health_overview_counts_strength_risk_and_watch_items():
    service = WatchlistService()
    items = [
        _item("strong", "up", 80, "strong", "low", judgement=True),
        _item("weak", "down", 20, "weak", "medium"),
        _item("risk", "sideways", 45, "neutral", "high"),
        _item("watch", "sideways", 50, "neutral", "medium"),
    ]

    overview = service._build_health_overview(items)

    assert overview.total_count == 4
    assert overview.strong_count == 1
    assert overview.weak_count == 1
    assert overview.high_risk_count == 1
    assert overview.watch_count == 1
    assert overview.active_judgment_count == 1
    assert 0 <= overview.health_score <= 100
    assert overview.label in {"偏强", "均衡", "偏弱", "风险偏高"}


def test_watchlist_health_overview_major_event_does_not_count_as_high_risk():
    service = WatchlistService()
    items = [
        _item("risk", "sideways", 45, "neutral", "high"),
        WatchlistItemSummary(
            ts_code="event_only",
            name="event_only",
            asof="2026-06-18",
            price=10.0,
            change_pct=None,
            trend=TrendResult(direction="sideways", strength=50, degraded=False, evidence=[]),
            relative_strength=RelativeStrengthSummary(label_20d="neutral"),
            capital_flow=CapitalFlowSummary(label="中性", available=True, degraded=False),
            risk=RiskSummary(level="medium"),
            events=EventSummary(flag="major", available=True),
            judgement=JudgementSummary(has_active=False),
        ),
    ]

    overview = service._build_health_overview(items)

    assert overview.high_risk_count == 1
    assert overview.watch_count == 1


def test_watchlist_health_overview_assigns_each_stock_to_one_bucket():
    service = WatchlistService()
    items = [
        _item("up_but_rs_weak", "up", 80, "weak", "low"),
        _item("down_but_rs_strong", "down", 30, "strong", "medium"),
        _item("plain_strong", "up", 75, "strong", "low"),
    ]

    overview = service._build_health_overview(items)

    assert overview.total_count == 3
    assert overview.strong_count == 1
    assert overview.weak_count == 2
    assert overview.high_risk_count == 0
    assert overview.watch_count == 0
    assert (
        overview.strong_count
        + overview.weak_count
        + overview.high_risk_count
        + overview.watch_count
    ) == overview.total_count


def test_watchlist_health_overview_builds_industry_exposure_and_concentration(monkeypatch):
    from services.a_share_industry_lookup import AShareIndustryLookup

    industry_map = {
        "600519": "白酒",
        "000001": "银行",
        "300750": "电气设备",
        "601318": "保险",
        "002594": "汽车",
    }
    monkeypatch.setattr(
        AShareIndustryLookup,
        "lookup",
        classmethod(lambda cls, ts_code: industry_map.get(ts_code.split(".")[0], None)),
    )

    service = WatchlistService()
    items = [
        _item("600519", "up", 80, "strong", "low"),
        _item("300750", "up", 75, "strong", "low"),
        _item("002594", "sideways", 55, "neutral", "medium"),
        _item("000001", "sideways", 50, "neutral", "low"),
    ]

    overview = service._build_health_overview(items)

    assert overview.industry_count == 4
    assert len(overview.top_industries) == 4
    industries = {item.industry for item in overview.top_industries}
    assert "白酒" in industries
    assert overview.concentration_level == "分散"


def test_watchlist_health_overview_uses_position_weights_for_concentration(monkeypatch):
    from services.a_share_industry_lookup import AShareIndustryLookup

    monkeypatch.setattr(
        AShareIndustryLookup,
        "lookup",
        classmethod(lambda cls, ts_code: {
            "600519": "白酒",
            "000001": "银行",
            "300750": "白酒",
        }.get(ts_code, "其他")),
    )

    service = WatchlistService()
    items = [
        _item("600519", "up", 80, "strong", "low"),
        _item("300750", "up", 75, "strong", "low"),
        _item("000001", "sideways", 50, "neutral", "low"),
    ]
    weights = {
        "600519": 50.0,
        "300750": 30.0,
        "000001": 20.0,
    }

    overview = service._build_health_overview(items, weights)

    assert overview.uses_position_weights is True
    assert overview.top_industries[0].industry == "白酒"
    assert overview.top_industries[0].weight_pct == 80.0
    assert overview.concentration_level == "偏高"
    assert "持仓权重" in overview.concentration_note
