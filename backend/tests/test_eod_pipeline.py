# backend/tests/test_eod_pipeline.py
import sys, os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # repo root

from tools.eod_pipeline import build_scan_payload


def _synthetic_df(rows=80, seed=42):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end="2026-06-10", periods=rows)
    close = 100 + np.cumsum(rng.normal(0, 1, rows))
    return pd.DataFrame({
        "Open": close + rng.normal(0, 0.5, rows),
        "High": close + 1.5,
        "Low": close - 1.5,
        "Close": close,
        "Volume": rng.integers(1000, 5000, rows),
    }, index=idx)


def test_build_scan_payload_signals_and_missing():
    history = {"AAA.NS": _synthetic_df()}
    payload = build_scan_payload([("AAA.NS", "Alpha"), ("BBB.NS", "Beta")], history)
    assert len(payload) == 2
    a, b = payload
    assert a["ticker"] == "AAA.NS" and a["signal"] in ("BUY", "SELL", "HOLD")
    assert isinstance(a["change_pct"], float)
    assert a["last_price"] is not None
    # ticker with no history degrades to None fields, not an exception
    assert b["signal"] is None and b["last_price"] is None and b["change_pct"] is None
