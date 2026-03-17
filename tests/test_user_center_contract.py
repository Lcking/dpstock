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
