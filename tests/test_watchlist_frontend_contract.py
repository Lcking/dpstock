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


def test_watchlist_page_supports_two_phase_summary_loading():
    watchlist_types = (REPO_ROOT / "frontend/src/types/watchlist.ts").read_text(encoding="utf-8")
    watchlist_view = (REPO_ROOT / "frontend/src/components/Watchlist/WatchlistList.vue").read_text(encoding="utf-8")
    api_service = (REPO_ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")

    assert "is_skeleton" in watchlist_types
    assert "on_risk_list" in watchlist_types
    assert "risk_list_hits" in watchlist_types
    assert "phase: 'fast'" in watchlist_view
    assert "phase: 'full'" in watchlist_view
    assert "detailLoading" in watchlist_view
    assert "命中风险股清单" in watchlist_view
    assert "phase?: 'fast' | 'full'" in api_service


def test_user_center_surfaces_trust_stats_and_risk_unread():
    overview_cards = (REPO_ROOT / "frontend/src/components/UserCenter/UserOverviewCards.vue").read_text(encoding="utf-8")
    user_center_page = (REPO_ROOT / "frontend/src/components/UserCenter/UserCenterPage.vue").read_text(encoding="utf-8")

    assert "历史验证与条件质量" in overview_cards
    assert "risk_alert_unread_count" in overview_cards
    assert "buildTrustSummary" in overview_cards
    assert "n-skeleton" in user_center_page.lower()


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
