from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_watchlist_page_surfaces_health_overview_scorecard():
    watchlist_types = (REPO_ROOT / "frontend/src/types/watchlist.ts").read_text(encoding="utf-8")
    watchlist_view = (REPO_ROOT / "frontend/src/components/Watchlist/WatchlistList.vue").read_text(encoding="utf-8")

    assert "WatchlistHealthOverview" in watchlist_types
    assert "health_overview" in watchlist_types
    assert "自选健康度" in watchlist_view
    assert "healthOverview" in watchlist_view
    assert "强势" in watchlist_view
    assert "弱势" in watchlist_view
    assert "高风险" in watchlist_view
    assert "待观察" in watchlist_view


def test_watchlist_binding_prompt_uses_server_temporary_state_only():
    watchlist_view = (REPO_ROOT / "frontend/src/components/Watchlist/WatchlistList.vue").read_text(encoding="utf-8")

    assert "watchlistState.value.isTemporary" in watchlist_view
    assert "hasAnchorToken" not in watchlist_view
