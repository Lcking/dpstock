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


def test_frontend_has_me_route_and_my_menu_entries():
    repo_root = Path(__file__).resolve().parents[1]
    router_text = (repo_root / "frontend/src/router/index.ts").read_text(encoding="utf-8")
    nav_text = (repo_root / "frontend/src/components/NavBar.vue").read_text(encoding="utf-8")

    assert "path: '/me'" in router_text
    assert "我的" in nav_text
    assert "我的观察" in nav_text
    assert "判断日记" in nav_text
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

    assert "position: sticky;" in nav_text
    assert "padding-top: 95px;" not in nav_text
    assert "padding-top: 71px;" not in nav_text
