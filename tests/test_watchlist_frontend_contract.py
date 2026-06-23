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


def test_watchlist_page_prompts_email_restore_on_new_device():
    watchlist_view = (REPO_ROOT / "frontend/src/components/Watchlist/WatchlistList.vue").read_text(encoding="utf-8")
    anchor_session = (REPO_ROOT / "frontend/src/utils/anchorSession.ts").read_text(encoding="utf-8")

    assert "needsSessionRestore" in watchlist_view
    assert "验证邮箱恢复" in watchlist_view
    assert "syncAnchorSession" in anchor_session
    assert "masked_email alone is not proof" in anchor_session


def test_quota_status_ui_does_not_default_to_five():
    quota_view = (REPO_ROOT / "frontend/src/components/QuotaStatus.vue").read_text(encoding="utf-8")
    invite_view = (REPO_ROOT / "frontend/src/components/InviteDialog.vue").read_text(encoding="utf-8")

    assert "DEFAULT_BASE_QUOTA = 3" in quota_view
    assert "|| 5" not in quota_view
    assert "total_quota || 5" not in invite_view


def test_anchor_token_requires_jwt_for_bound_state():
    anchor_token = (REPO_ROOT / "frontend/src/utils/anchorToken.ts").read_text(encoding="utf-8")

    assert "localStorage.getItem('token')" in anchor_token
    assert "MASKED_EMAIL_KEY" in anchor_token


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
    assert "compareRiskHits" in watchlist_view
    assert "weightNote" in watchlist_view
    assert "focus === 'risk'" in watchlist_view
    assert "phase?: 'fast' | 'full'" in api_service


def test_analysis_results_surface_data_provenance():
    analysis_app = (REPO_ROOT / "frontend/src/components/StockAnalysisApp.vue").read_text(encoding="utf-8")
    stock_card = (REPO_ROOT / "frontend/src/components/StockCard.vue").read_text(encoding="utf-8")

    assert "latestProvenanceLabel" in analysis_app
    assert "dataProvenanceLabel" in analysis_app
    assert "data-provenance" in stock_card


def test_user_center_surfaces_personal_review_and_guest_conversion():
    overview_cards = (REPO_ROOT / "frontend/src/components/UserCenter/UserOverviewCards.vue").read_text(encoding="utf-8")
    user_center_page = (REPO_ROOT / "frontend/src/components/UserCenter/UserCenterPage.vue").read_text(encoding="utf-8")

    assert "我的复盘表现" in overview_cards
    assert "buildPersonalReviewSummary" in overview_cards
    assert "judgment_count" in overview_cards
    assert "guestAssetSummary" in user_center_page
    assert "focus: 'risk'" in user_center_page


def test_user_center_surfaces_trust_stats_and_risk_unread():
    overview_cards = (REPO_ROOT / "frontend/src/components/UserCenter/UserOverviewCards.vue").read_text(encoding="utf-8")
    user_center_page = (REPO_ROOT / "frontend/src/components/UserCenter/UserCenterPage.vue").read_text(encoding="utf-8")

    assert "我的复盘表现" in overview_cards
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
