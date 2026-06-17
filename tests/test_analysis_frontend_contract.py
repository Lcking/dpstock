from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_analysis_v1_display_surfaces_plain_language_summary_without_advice_words():
    component_text = (REPO_ROOT / "frontend/src/components/AnalysisV1Display.vue").read_text(encoding="utf-8")

    assert "一句话结论" in component_text
    assert "plainLanguageSummary" in component_text
    assert "buildPlainLanguageSummary" in component_text
    assert "为什么这么判" in component_text
    assert "evidenceItems" in component_text
    assert "buildEvidenceItems" in component_text
    assert "结构依据" in component_text
    assert "指标依据" in component_text
    assert "风险依据" in component_text
    assert "结构" in component_text
    assert "风险" in component_text

    summary_section = component_text[
        component_text.index("plainLanguageSummary"):
        component_text.index("<!-- Section 1: 结构快照 -->")
    ]
    assert "买入" not in summary_section
    assert "卖出" not in summary_section
    assert "推荐" not in summary_section
