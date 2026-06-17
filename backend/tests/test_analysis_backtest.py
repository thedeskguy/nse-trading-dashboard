"""Smoke test for backtest v2 result shape at backend level."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
import pandas as pd
from tools import backtester


def test_backtest_result_has_v2_fields():
    """Verify that run_backtest returns the v2 result schema with open_position."""
    n = 120
    closes = np.linspace(100, 200, n)
    df = pd.DataFrame({
        "Open": closes, "High": closes + 1, "Low": closes - 1,
        "Close": closes, "Volume": [1_000_000] * n,
    }, index=pd.date_range("2025-01-01", periods=n, freq="D"))

    res = backtester.run_backtest(df, strategy="indicator")

    # v2 contract: open_position + new stats
    assert "open_position" in res, "Result missing 'open_position' field"
    assert isinstance(res["open_position"], (dict, type(None)))

    # v2 stats must include CAGR, Sortino, Calmar
    assert isinstance(res["stats"], dict), "stats is not a dict"
    assert {"cagr_pct", "sortino_ratio", "calmar_ratio"} <= set(
        res["stats"]
    ), f"Missing v2 stats. Got: {set(res['stats'].keys())}"


def test_backtest_trend_preset_shape():
    """Verify that trend preset strategy returns v2 result schema."""
    n = 260
    closes = np.linspace(100, 200, n)
    df = pd.DataFrame({
        "Open": closes, "High": closes + 1, "Low": closes - 1,
        "Close": closes, "Volume": [1_000_000] * n,
    }, index=pd.date_range("2025-01-01", periods=n, freq="D"))

    from tools.compute_indicators import compute_all
    res = backtester.run_backtest(compute_all(df), strategy="trend")

    assert res["error"] is None
    assert res["strategy"] == "trend"
    assert "open_position" in res
