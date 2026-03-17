from pathlib import Path


def test_binding_prompts_contract():
    repo_root = Path(__file__).resolve().parents[1]

    watchlist_text = (repo_root / "frontend/src/components/Watchlist/WatchlistList.vue").read_text(encoding="utf-8")
    analysis_text = (repo_root / "frontend/src/components/AnalysisV1Display.vue").read_text(encoding="utf-8")
    quota_modal_text = (repo_root / "frontend/src/components/QuotaExceededModal.vue").read_text(encoding="utf-8")
    nav_text = (repo_root / "frontend/src/components/NavBar.vue").read_text(encoding="utf-8")
    stock_card_text = (repo_root / "frontend/src/components/StockCard.vue").read_text(encoding="utf-8")

    assert "绑定邮箱，保存你的观察资产" in watchlist_text
    assert "绑定后可持续追踪复盘" in analysis_text
    assert "绑定后可解锁邀请奖励与更多额度" in quota_modal_text
    assert "绑定邮箱" in nav_text
    assert "绑定后资产不会因换设备或清缓存而丢失" in stock_card_text
