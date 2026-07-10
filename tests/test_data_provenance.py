import pandas as pd
from datetime import datetime

from services.data_provenance import build_data_provenance, resolve_data_source
from services.stock_scorer import StockScorer


def test_resolve_data_source_by_market():
    assert resolve_data_source("A") == "akshare / tushare"
    assert resolve_data_source("HK") == "雅虎财经"


def test_build_data_provenance_uses_latest_bar_timestamp():
    df = pd.DataFrame(
        {"Close": [10.0, 10.5]},
        index=pd.to_datetime(["2026-06-17", "2026-06-18"]),
    )
    provenance = build_data_provenance("A", df)

    assert provenance["data_as_of"] == "2026-06-18 00:00"
    assert provenance["data_source"] == "akshare / tushare"
    assert "数据截至" in provenance["data_provenance_label"]


def test_build_data_provenance_marks_realtime_patch():
    df = pd.DataFrame(
        {"Close": [10.72, 10.66]},
        index=pd.to_datetime(["2026-07-09", "2026-07-10"]),
    )
    df.attrs["realtime_patched"] = True
    df.attrs["realtime_as_of"] = "2026-07-10 15:18:45"
    provenance = build_data_provenance("A", df)
    assert provenance["data_source"] == "日线 + 新浪实时补丁"
    assert provenance["data_as_of"] == "2026-07-10 15:18"


def test_stock_scorer_recommendation_uses_structure_labels():
    scorer = StockScorer()
    assert scorer.get_recommendation(85) == "结构强"
    assert scorer.get_recommendation(65) == "中性"
    assert scorer.get_recommendation(25) == "结构弱"
