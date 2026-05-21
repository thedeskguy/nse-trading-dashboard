"""Unit tests for tools/backtester.py — no external API calls."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pandas as pd
import numpy as np
from tools.backtester import run_backtest, WARMUP


def _make_df(n: int = 100) -> pd.DataFrame:
    """Minimal indicator-enriched df that satisfies generate_signal()."""
    rng = np.random.default_rng(42)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    closes = 100 + np.cumsum(rng.normal(0, 0.5, n))
    df = pd.DataFrame(
        {
            "Open":   closes * 0.999,
            "High":   closes * 1.005,
            "Low":    closes * 0.995,
            "Close":  closes,
            "Volume": np.full(n, 1_000_000, dtype=float),
            "RSI_14":       np.full(n, 65.0),
            "MACD":         np.full(n, 0.1),
            "MACD_signal":  np.full(n, 0.05),
            "EMA_9":        closes * 0.99,
            "EMA_21":       closes * 0.98,
            "EMA_50":       closes * 0.97,
            "EMA_200":      closes * 0.96,
            "BB_upper":     closes * 1.03,
            "BB_lower":     closes * 0.97,
            "BB_middle":    closes,
            "BB_bandwidth": np.full(n, 0.06),
            "BB_pct":       np.full(n, 0.5),
            "ATR_14":       np.full(n, 1.0),
            "OBV":          np.cumsum(np.full(n, 1000.0)),
        },
        index=idx,
    )
    df.attrs["support"] = None
    df.attrs["resistance"] = None
    return df


def test_run_backtest_returns_expected_keys():
    result = run_backtest(_make_df(100))
    assert "trades" in result
    assert "equity_curve" in result
    assert "stats" in result


def test_run_backtest_short_df_returns_empty():
    """DataFrame shorter than WARMUP+2 must return empty result gracefully."""
    result = run_backtest(_make_df(WARMUP - 1))
    assert result["trades"] == []
    assert result["stats"]["num_trades"] == 0


def test_equity_curve_starts_at_100():
    result = run_backtest(_make_df(100))
    if result["equity_curve"]:
        assert result["equity_curve"][0]["equity"] == 100.0


def test_stats_win_rate_bounded():
    result = run_backtest(_make_df(120))
    assert 0.0 <= result["stats"]["win_rate"] <= 1.0


def test_all_pnl_values_are_finite():
    result = run_backtest(_make_df(100))
    for trade in result["trades"]:
        assert isinstance(trade["pnl_pct"], float)
        assert not (trade["pnl_pct"] != trade["pnl_pct"])  # not NaN
