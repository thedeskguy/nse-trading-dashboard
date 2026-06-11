import sys, os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # repo root

from tools.price_store import df_to_rows, rows_to_df


def _sample_df():
    idx = pd.to_datetime(["2026-06-08", "2026-06-09", "2026-06-10"])
    return pd.DataFrame({
        "Open":   [100.0, 101.0, 102.0],
        "High":   [101.5, 102.5, 103.5],
        "Low":    [99.5, 100.5, 101.5],
        "Close":  [101.0, 102.0, 103.0],
        "Volume": [1000, 1100, 1200],
    }, index=idx)


def test_df_to_rows_shape():
    rows = df_to_rows("RELIANCE.NS", _sample_df())
    assert len(rows) == 3
    assert rows[0] == {
        "ticker": "RELIANCE.NS", "date": "2026-06-08",
        "open": 100.0, "high": 101.5, "low": 99.5, "close": 101.0, "volume": 1000,
    }


def test_round_trip():
    df = _sample_df()
    out = rows_to_df(df_to_rows("X.NS", df))
    pd.testing.assert_frame_equal(out, df, check_dtype=False)


def test_rows_to_df_empty():
    assert rows_to_df([]).empty
