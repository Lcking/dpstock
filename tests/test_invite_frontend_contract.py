from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_admin_invite_tab_labels_generated_links_as_funnel_not_successful_invites():
    admin_view = (REPO_ROOT / "frontend/src/components/Admin/AdminDashboard.vue").read_text(encoding="utf-8")

    assert "生成链接用户数" in admin_view
    assert "接受邀请数" in admin_view
    assert "奖励发放数" in admin_view
    assert "接受率" in admin_view
    assert "奖励转化率" in admin_view
    assert "邀请码总数" not in admin_view
