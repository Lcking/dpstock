from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_analysis_v1_persists_judgment_candidate_descriptions():
    component = (REPO_ROOT / "frontend/src/components/AnalysisV1Display.vue").read_text(encoding="utf-8")

    assert "judgment_zone.candidates.map" in component
    assert "option_id" in component
    assert "description" in component
    assert "selected_candidate_description" in component


def test_journal_review_surfaces_system_evaluation_summary():
    api_service = (REPO_ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
    review_dialog = (REPO_ROOT / "frontend/src/components/Journal/JournalReviewDialog.vue").read_text(encoding="utf-8")
    detail_dialog = (REPO_ROOT / "frontend/src/components/Journal/JournalDetailDialog.vue").read_text(encoding="utf-8")

    assert "getRecordEvaluation" in api_service
    assert "/evaluation" in api_service
    assert "system_evaluation" in review_dialog
    assert "系统判卷" in review_dialog
    assert "system_evaluation" in detail_dialog
    assert "实际路径" in detail_dialog


def test_journal_detail_uses_saved_candidate_condition_not_hardcoded_direction():
    detail_dialog = (REPO_ROOT / "frontend/src/components/Journal/JournalDetailDialog.vue").read_text(encoding="utf-8")
    list_view = (REPO_ROOT / "frontend/src/components/Journal/JournalList.vue").read_text(encoding="utf-8")

    assert "selectedCandidateDescription" in detail_dialog
    assert "candidateDescription(record)" in detail_dialog
    assert "B - 看跌/做空" not in detail_dialog
    assert "C - 观望/不确定" not in detail_dialog
    assert "getSelectedCandidateDescription(record)" in list_view
    assert "B: '看跌'" not in list_view
