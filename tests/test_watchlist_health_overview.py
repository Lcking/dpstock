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
