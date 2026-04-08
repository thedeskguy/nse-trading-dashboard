"""
Real-time OHLCV fetcher for NSE equities via Angel One SmartAPI.
Uses searchScrip (tiny API call) for token lookup — no large master file download.
Falls back to yfinance automatically on any failure.
"""

import time
import json
import os
import pandas as pd
from datetime import datetime, timedelta

# ── Interval mapping ────────────────────────────────────────────────────────────
ANGEL_INTERVAL_MAP = {
    "5m":  "FIVE_MINUTE",
    "15m": "FIFTEEN_MINUTE",
    "30m": "THIRTY_MINUTE",
    "1h":  "ONE_HOUR",
    "1d":  "ONE_DAY",
}

MAX_LOOKBACK_DAYS = {
    "FIVE_MINUTE":    90,
    "FIFTEEN_MINUTE": 180,
    "THIRTY_MINUTE":  180,
    "ONE_HOUR":       400,
    "ONE_DAY":        2000,
}

PERIOD_TO_DAYS = {
    "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
    "6mo": 180, "1y": 365, "2y": 730, "5y": 1825,
}

# Disk cache for token lookups so we don't hit searchScrip repeatedly
TOKEN_CACHE_FILE = ".tmp/angel_tokens.json"
_token_cache: dict = {}
_token_cache_loaded = False


def _load_token_cache() -> None:
    global _token_cache, _token_cache_loaded
    if _token_cache_loaded:
        return
    os.makedirs(".tmp", exist_ok=True)
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            with open(TOKEN_CACHE_FILE, "r") as f:
                _token_cache = json.load(f)
        except Exception:
            _token_cache = {}
    _token_cache_loaded = True


def _save_token_cache() -> None:
    try:
        os.makedirs(".tmp", exist_ok=True)
        with open(TOKEN_CACHE_FILE, "w") as f:
            json.dump(_token_cache, f)
    except Exception:
        pass


def _bare_symbol(ticker: str) -> str:
    """Strip .NS / .BO suffix and upper-case."""
    t = ticker.strip().upper()
    for suffix in (".NS", ".BO"):
        if t.endswith(suffix):
            t = t[: -len(suffix)]
    return t


def get_equity_token(ticker: str) -> str | None:
    """
    Look up NSE equity token via Angel One searchScrip.
    Caches results to disk so each symbol is only looked up once.
    Returns token string or None.
    """
    if ticker.startswith("^"):
        return None  # index tickers — use yfinance

    bare = _bare_symbol(ticker)
    _load_token_cache()

    if bare in _token_cache:
        return _token_cache[bare]

    try:
        from tools.angel_auth import get_session
        obj = get_session()
        result = obj.searchScrip("NSE", bare)
        data = (result or {}).get("data") or []
        # Prefer exact EQ match (avoids futures/options contamination)
        token = None
        for item in data:
            sym = item.get("tradingsymbol", "")
            if sym == f"{bare}-EQ" or sym == bare:
                token = item.get("symboltoken")
                break
        # Fallback: first result
        if token is None and data:
            token = data[0].get("symboltoken")

        if token:
            _token_cache[bare] = token
            _save_token_cache()
        return token
    except Exception:
        return None


def fetch_angel_ohlcv(
    ticker: str,
    interval: str = "1d",
    period: str = "3mo",
) -> pd.DataFrame | None:
    """
    Fetch OHLCV from Angel One getCandleData.
    Returns DataFrame[Open, High, Low, Close, Volume] with IST DatetimeIndex,
    or None on any failure (caller falls back to yfinance).
    """
    if ticker.startswith("^"):
        return None

    resample_weekly = (interval == "1wk")
    fetch_interval = "1d" if resample_weekly else interval
    angel_interval = ANGEL_INTERVAL_MAP.get(fetch_interval)
    if angel_interval is None:
        return None

    days = PERIOD_TO_DAYS.get(period, 90)
    days = min(days, MAX_LOOKBACK_DAYS.get(angel_interval, 365))

    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    from_dt = ist_now - timedelta(days=days)
    fmt = "%Y-%m-%d 09:15" if angel_interval == "ONE_DAY" else "%Y-%m-%d %H:%M"
    from_str = from_dt.strftime(fmt)
    to_str   = ist_now.strftime(fmt)

    token = get_equity_token(ticker)
    if not token:
        return None

    try:
        from tools.angel_auth import get_session, reset_session
        obj = get_session()
        params = {
            "exchange":    "NSE",
            "symboltoken": token,
            "interval":    angel_interval,
            "fromdate":    from_str,
            "todate":      to_str,
        }
        resp = obj.getCandleData(params)

        # Retry once on auth failure
        if not resp or resp.get("status") is False:
            reset_session()
            obj = get_session()
            resp = obj.getCandleData(params)
    except Exception:
        return None

    data = (resp or {}).get("data")
    if not data:
        return None

    try:
        df = pd.DataFrame(data, columns=["datetime", "Open", "High", "Low", "Close", "Volume"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        if df["datetime"].dt.tz is None:
            df["datetime"] = df["datetime"].dt.tz_localize("Asia/Kolkata")
        else:
            df["datetime"] = df["datetime"].dt.tz_convert("Asia/Kolkata")
        df = df.set_index("datetime").sort_index()
        df = df.apply(pd.to_numeric, errors="coerce")
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        df = df[df["Volume"] >= 0]
    except Exception:
        return None

    if df.empty:
        return None

    if resample_weekly:
        df = df.resample("W-FRI").agg(
            {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
        ).dropna()

    return df
