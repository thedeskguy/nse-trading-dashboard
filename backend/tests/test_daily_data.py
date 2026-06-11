# backend/tests/test_daily_data.py
import asyncio
import sys, os
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))             # repo root

import services.daily_data as daily_data
from services.daily_data import get_daily_df, last_expected_session, resample_ohlcv


def _daily_df(end, rows=30):
    idx = pd.bdate_range(end=end, periods=rows)
    close = np.linspace(100, 110, rows)
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1,
                         "Close": close, "Volume": [1000] * rows}, index=idx)


def test_resample_weekly():
    df = _daily_df("2026-06-05", rows=10)  # two full Mon-Fri weeks
    wk = resample_ohlcv(df, "W-FRI")
    assert len(wk) == 2
    first = df.iloc[:5]
    assert wk["Open"].iloc[0] == first["Open"].iloc[0]
    assert wk["High"].iloc[0] == first["High"].max()
    assert wk["Low"].iloc[0] == first["Low"].min()
    assert wk["Close"].iloc[0] == first["Close"].iloc[-1]
    assert wk["Volume"].iloc[0] == first["Volume"].sum()


def test_last_expected_session_weekend():
    sat = datetime(2026, 6, 13, 12, 0, tzinfo=daily_data._IST)  # Saturday
    assert last_expected_session(sat).weekday() == 4             # -> Friday


def test_store_hit_no_live_fetch(monkeypatch):
    fresh = _daily_df(pd.Timestamp(last_expected_session()))
    from tools import price_store
    monkeypatch.setattr(price_store, "is_configured", lambda: True)
    monkeypatch.setattr(price_store, "get_history", lambda t, d: fresh)
    monkeypatch.setattr(daily_data, "is_market_open", lambda: False)

    import tools.fetch_stock_data as fsd

    def _boom(*a, **k):
        raise AssertionError("live fetch should not happen on a fresh store hit")

    monkeypatch.setattr(fsd, "_fetch_yfinance", _boom)
    monkeypatch.setattr(fsd, "fetch_ohlcv", _boom)

    df = asyncio.run(get_daily_df("TESTHIT.NS", "3mo"))
    assert len(df) == len(fresh)


def test_store_miss_falls_back(monkeypatch):
    from tools import price_store
    monkeypatch.setattr(price_store, "is_configured", lambda: True)
    monkeypatch.setattr(price_store, "get_history", lambda t, d: pd.DataFrame())

    fallback = _daily_df("2026-06-10")
    import tools.fetch_stock_data as fsd
    monkeypatch.setattr(fsd, "fetch_ohlcv", lambda *a, **k: fallback)

    df = asyncio.run(get_daily_df("TESTMISS.NS", "3mo"))
    assert len(df) == len(fallback)
