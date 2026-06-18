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


def test_watchlist_page_surfaces_risk_alert_panel_and_notification_polling():
    watchlist_types = (REPO_ROOT / "frontend/src/types/watchlist.ts").read_text(encoding="utf-8")
    watchlist_view = (REPO_ROOT / "frontend/src/components/Watchlist/WatchlistList.vue").read_text(encoding="utf-8")
    api_service = (REPO_ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
    notification_store = (REPO_ROOT / "frontend/src/stores/notification.ts").read_text(encoding="utf-8")
    navbar = (REPO_ROOT / "frontend/src/components/NavBar.vue").read_text(encoding="utf-8")

    assert "WatchlistRiskAlert" in watchlist_types
    assert "getWatchlistRiskAlerts" in api_service
    assert "/watchlists/risk-alerts" in api_service
    assert "自选风险提醒" in watchlist_view
    assert "loadRiskAlerts" in watchlist_view
    assert "getWatchlistRiskAlertUnreadCount" in notification_store
    assert "totalNotificationCount" in navbar
