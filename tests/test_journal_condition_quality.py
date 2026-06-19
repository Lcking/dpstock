from services.journal.condition_quality import (
    build_condition_quality_leaderboard,
    classify_condition_description,
    extract_selected_condition_description,
)


def test_classify_breakout_with_volume_condition():
    profile = classify_condition_description(
        "价格突破10.13（近30日最高价）且成交量连续2日高于20日均量1.5倍。"
    )

    assert profile == {"key": "breakout_volume", "label": "突破+放量"}


def test_classify_range_with_shrink_volume_condition():
    profile = classify_condition_description(
        "价格在9.0-9.5区间震荡超过3个交易日，成交量回落至20日均量的0.8-1.2倍。"
    )

    assert profile == {"key": "range_shrink_volume", "label": "区间震荡+缩量"}


def test_extract_selected_condition_description_from_constraints():
    constraints = {
        "candidates": {
            "A": "价格突破10.13且成交量连续2日高于20日均量1.5倍。",
            "B": "价格在9.0-9.5区间震荡超过3个交易日。",
        }
    }

    description = extract_selected_condition_description(constraints, "A")

    assert "突破10.13" in description


def test_build_condition_quality_leaderboard_groups_outcomes_by_condition_type():
    leaderboard = build_condition_quality_leaderboard(
        [
            {
                "outcome": "supported",
                "condition_description": "价格突破10.13且成交量连续2日高于20日均量1.5倍。",
            },
            {
                "outcome": "falsified",
                "condition_description": "价格突破11.20且成交量连续2日高于20日均量1.5倍。",
            },
            {
                "outcome": "uncertain",
                "condition_description": "价格在9.0-9.5区间震荡超过3个交易日，成交量回落至20日均量的0.8-1.2倍。",
            },
            {
                "outcome": "supported",
                "condition_description": "价格突破12.00且成交量连续2日高于20日均量1.5倍。",
            },
        ]
    )

    assert len(leaderboard) == 2
    assert leaderboard[0]["key"] == "breakout_volume"
    assert leaderboard[0]["label"] == "突破+放量"
    assert leaderboard[0]["reviewed_count"] == 3
    assert leaderboard[0]["supported_count"] == 2
    assert leaderboard[0]["falsified_count"] == 1
    assert leaderboard[0]["support_rate"] == 66.67
    assert leaderboard[1]["key"] == "range_shrink_volume"
    assert leaderboard[1]["reviewed_count"] == 1
