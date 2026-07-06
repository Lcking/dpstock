from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_deploy_checklist_script_covers_current_surfaces():
    script = (REPO_ROOT / "scripts/verify_deploy_checklist.sh").read_text(encoding="utf-8")

    assert "/api/health" in script
    assert "/risk-stocks" in script
    assert "/me/weekly-recap" in script
    assert 'check_redirect "/review/weekly"' in script
    assert "/api/user-center/weekly-recap" in script
    assert "/api/kline/159941" in script
    assert "review/weekly" in script
    assert 'check_absent_grep "/sitemap-core.xml"' in script
    assert "历史验证|仅供参考" not in script
