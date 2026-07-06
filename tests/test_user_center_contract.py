from pathlib import Path

from fastapi.testclient import TestClient

from web_server import app


def test_user_center_overview_endpoint_exists():
    with TestClient(app) as client:
        response = client.get("/api/user-center/overview")

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "quota_status" in data
        assert "watchlist_count" in data
        assert "due_count" in data
        assert "recent_judgments" in data
        assert "trust_stats" in data
        assert "personal_review_stats" in data
        assert "judgment_count" in data
        assert "risk_alert_unread_count" in data
        assert "reviewed_count" in data["trust_stats"]
        assert "condition_quality_leaderboard" in data["trust_stats"]
        assert "reviewed_count" in data["personal_review_stats"]
        assert "notify_pref" in data["user"]
        assert "risk_alert_email" in data["user"]["notify_pref"]
        assert "journal_due_email" in data["user"]["notify_pref"]


def test_user_center_weekly_recap_endpoint_exists():
    with TestClient(app) as client:
        response = client.get("/api/user-center/weekly-recap")

        assert response.status_code == 200
        data = response.json()
        assert data["scope"] == "user"
        assert "period_label" in data
        assert "stats" in data
        assert "highlight_cases" in data
        assert "due_count" in data
        assert "reviewed_count" in data["stats"]


def test_frontend_has_me_route_and_my_menu_entries():
    repo_root = Path(__file__).resolve().parents[1]
    router_text = (repo_root / "frontend/src/router/index.ts").read_text(encoding="utf-8")
    nav_text = (repo_root / "frontend/src/components/NavBar.vue").read_text(encoding="utf-8")

    assert "path: '/me'" in router_text
    assert "path: '/me/weekly-recap'" in router_text
    assert "我的" in nav_text
    assert "我的观察" in nav_text
    assert "判断日记" in nav_text
    assert "判断验证周报" in nav_text
    assert "/me/weekly-recap" in nav_text
    assert "用户中心" in nav_text
    assert "额度与邀请" in nav_text


def test_nav_bar_places_my_menu_after_bind_entry():
    repo_root = Path(__file__).resolve().parents[1]
    nav_text = (repo_root / "frontend/src/components/NavBar.vue").read_text(encoding="utf-8")
    template_text = nav_text.split("<script setup", 1)[0]

    analysis_idx = template_text.index('to="/analysis"')
    strategy_idx = template_text.index('v-for="link in links"')
    bind_idx = template_text.index("v-if=\"anchorMode === 'anonymous'\"")
    my_idx = template_text.rindex('@select="handleMyMenuSelect"')

    assert analysis_idx < strategy_idx < bind_idx < my_idx


def test_nav_bar_uses_sticky_layout_instead_of_fixed_body_padding():
    repo_root = Path(__file__).resolve().parents[1]
    nav_text = (repo_root / "frontend/src/components/NavBar.vue").read_text(encoding="utf-8")

    assert "position: fixed;" in nav_text
    assert "nav-spacer" in nav_text
    assert "padding-top: 95px;" not in nav_text
    assert "padding-top: 71px;" not in nav_text


def test_public_frontend_no_longer_exposes_secret_admin_entry():
    repo_root = Path(__file__).resolve().parents[1]
    router_text = (repo_root / "frontend/src/router/index.ts").read_text(encoding="utf-8")
    footer_text = (repo_root / "frontend/src/components/Footer.vue").read_text(encoding="utf-8")

    assert "path: '/secret-admin'" not in router_text
    assert 'to="/secret-admin"' not in footer_text
    # 正式管理入口为 /admin（独立 admin JWT），不得再使用旧 /secret-admin
    assert "path: '/admin'" in router_text or 'path: "/admin"' in router_text
