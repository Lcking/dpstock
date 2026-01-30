import pandas as pd

from services.technical_indicator import TechnicalIndicator


def test_calculate_indicators_includes_ma200_when_enough_rows():
    n = 260  # > 200 trading days
    df = pd.DataFrame(
        {
            "Open": [10.0] * n,
            "High": [10.5] * n,
            "Low": [9.5] * n,
            "Close": [10.0 + i * 0.01 for i in range(n)],
            "Volume": [1000] * n,
        }
    )

    ti = TechnicalIndicator()
    out = ti.calculate_indicators(df)

    assert "MA200" in out.columns
    # last MA200 should be a real number (not NaN) when n>=200
    assert pd.notna(out.iloc[-1]["MA200"])

