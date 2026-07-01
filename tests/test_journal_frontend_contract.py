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


def test_journal_list_surfaces_review_stats_scorecard():
    api_service = (REPO_ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
    journal_types = (REPO_ROOT / "frontend/src/types/journal.ts").read_text(encoding="utf-8")
    list_view = (REPO_ROOT / "frontend/src/components/Journal/JournalList.vue").read_text(encoding="utf-8")

    assert "JournalReviewStats" in journal_types
    assert "getJournalStats" in api_service
    assert "/journal/stats" in api_service
    assert "复盘统计" in list_view
    assert "support_rate" in list_view
    assert "most_common_failure_reason_label" in list_view
    assert "最常失败原因" in list_view
    assert "condition_quality_leaderboard" in journal_types
    assert "JournalConditionQualityItem" in journal_types
    assert "ConditionQualityLeaderboard" in list_view
    assert "loadReviewStats" in list_view


def test_journal_list_and_review_dialog_use_evaluation_preview():
    journal_types = (REPO_ROOT / "frontend/src/types/journal.ts").read_text(encoding="utf-8")
    list_view = (REPO_ROOT / "frontend/src/components/Journal/JournalList.vue").read_text(encoding="utf-8")
    review_dialog = (REPO_ROOT / "frontend/src/components/Journal/JournalReviewDialog.vue").read_text(encoding="utf-8")
    detail_dialog = (REPO_ROOT / "frontend/src/components/Journal/JournalDetailDialog.vue").read_text(encoding="utf-8")

    assert "evaluation_preview?: JournalSystemEvaluation" in journal_types
    assert "record.evaluation_preview" in list_view
    assert "系统初判" in list_view
    assert "props.record?.evaluation_preview" in review_dialog
    assert "effectiveSystemEvaluation" in detail_dialog
    assert "record.evaluation_preview" in detail_dialog
    assert "系统初判" in detail_dialog


def test_journal_review_captures_lesson_summary():
    journal_types = (REPO_ROOT / "frontend/src/types/journal.ts").read_text(encoding="utf-8")
    review_dialog = (REPO_ROOT / "frontend/src/components/Journal/JournalReviewDialog.vue").read_text(encoding="utf-8")
    detail_dialog = (REPO_ROOT / "frontend/src/components/Journal/JournalDetailDialog.vue").read_text(encoding="utf-8")
    api_service = (REPO_ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")

    assert "lesson?: string" in journal_types
    assert "lesson" in review_dialog
    assert "这次学到了什么" in review_dialog
    assert "apiService.reviewRecord" in review_dialog
    assert "lesson.value" in review_dialog
    assert "failureReason.value" in review_dialog
    assert "review.lesson" in detail_dialog
    assert "学习总结" in detail_dialog
    assert "lesson" in api_service


def test_journal_review_captures_failure_reason():
    journal_types = (REPO_ROOT / "frontend/src/types/journal.ts").read_text(encoding="utf-8")
    review_dialog = (REPO_ROOT / "frontend/src/components/Journal/JournalReviewDialog.vue").read_text(encoding="utf-8")
    detail_dialog = (REPO_ROOT / "frontend/src/components/Journal/JournalDetailDialog.vue").read_text(encoding="utf-8")
    api_service = (REPO_ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")

    assert "failure_reason?: JournalFailureReason" in journal_types
    assert "失败原因分类" in review_dialog
    assert "failureReason" in review_dialog
    assert "failure_reason" in api_service
    assert "failureReasonLabel" in detail_dialog
    assert "失败原因" in detail_dialog


def test_journal_list_supports_stock_timeline_filter():
    api_service = (REPO_ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
    journal_types = (REPO_ROOT / "frontend/src/types/journal.ts").read_text(encoding="utf-8")
    list_view = (REPO_ROOT / "frontend/src/components/Journal/JournalList.vue").read_text(encoding="utf-8")
    admin_view = (REPO_ROOT / "frontend/src/components/Admin/AdminDashboard.vue").read_text(encoding="utf-8")

    assert "JournalStockTimeline" in journal_types
    assert "getJournalStockTimeline" in api_service
    assert "/journal/stock-timeline" in api_service
    assert "stockFilter" in list_view
    assert "stock-timeline-panel" in list_view
    assert "clearStockFilter" in list_view
    assert "route.query.ts_code" in list_view
    assert "邮件投递" in admin_view
    assert "opsRiskEmailCols" in admin_view
    assert "opsJournalDueEmailCols" in admin_view
    assert "journal_due_email" in admin_view


def test_condition_quality_leaderboard_component_is_reused():
    leaderboard = (
        REPO_ROOT / "frontend/src/components/Journal/ConditionQualityLeaderboard.vue"
    ).read_text(encoding="utf-8")
    list_view = (REPO_ROOT / "frontend/src/components/Journal/JournalList.vue").read_text(encoding="utf-8")
    overview_cards = (
        REPO_ROOT / "frontend/src/components/UserCenter/UserOverviewCards.vue"
    ).read_text(encoding="utf-8")

    assert "condition-leaderboard" in leaderboard
    assert "formatSupportRate" in leaderboard
    assert "ConditionQualityLeaderboard" in list_view
    assert "stockTimelineLeaderboard" in list_view
    assert "ConditionQualityLeaderboard" in overview_cards
    assert "personalLeaderboard" in overview_cards


def test_journal_review_dialog_surfaces_review_suggestions():
    journal_types = (REPO_ROOT / "frontend/src/types/journal.ts").read_text(encoding="utf-8")
    review_dialog = (REPO_ROOT / "frontend/src/components/Journal/JournalReviewDialog.vue").read_text(encoding="utf-8")

    assert "JournalReviewSuggestions" in journal_types
    assert "review_suggestions" in journal_types
    assert "reviewSuggestions" in review_dialog
    assert "suggestion-bullets" in review_dialog
    assert "notesPlaceholder" in review_dialog
    assert "lessonPlaceholder" in review_dialog
    assert "suggested_failure_reason" in review_dialog
