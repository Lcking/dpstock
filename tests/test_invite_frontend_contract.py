from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_admin_invite_tab_labels_generated_links_as_funnel_not_successful_invites():
    admin_view = (REPO_ROOT / "frontend/src/components/Admin/AdminDashboard.vue").read_text(encoding="utf-8")

    assert "生成链接用户数" in admin_view
    assert "接受邀请数" in admin_view
    assert "奖励发放数" in admin_view
    assert "接受率" in admin_view
    assert "奖励转化率" in admin_view
    assert "待转化邀请" in admin_view
    assert "最近接受邀请" in admin_view
    assert "pending_first_analysis" in admin_view
    assert "邀请码总数" not in admin_view


def test_invited_landing_page_has_persistent_first_analysis_guidance():
    app_view = (REPO_ROOT / "frontend/src/components/StockAnalysisApp.vue").read_text(encoding="utf-8")

    assert "inviteAcceptedBanner" in app_view
    assert "完成首次股票分析后" in app_view
    assert "立即分析一只股票" in app_view
