"""
Store-first daily OHLCV access, shared by /market/signal, /market/ohlcv,
/analysis/confluence, /analysis/ml-predict and /analysis/backtest.

Read order:
  1. Supabase price_history (filled nightly by tools/eod_pipeline.py)
  2. + cheap 5-day yfinance top-up when the market is open or the store lags
  3. Full yfinance/Angel fetch only when the store has nothing for the ticker.
"""
import asyncio
from datetime import date, datetime, time as dtime, timedelta, timezone

import pandas as pd

from services.cache import cached
from services.logger import get_logger
from services.market_hours import adaptive_ttl, is_market_open

log = get_logger(__name__)

_IST = timezone(timedelta(hours=5, minutes=30))

# period -> calendar days (margin included for weekends/holidays)
PERIOD_DAYS = {
    "1mo": 35, "3mo": 100, "6mo": 190, "1y": 380,
    "2y": 745, "5y": 1840, "10y": 3700, "ytd": 380, "max": 7400,
}

_OHLC_AGG = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample daily bars to weekly ('W-FRI') or monthly ('ME') candles."""
    out = df.resample(rule).agg(_OHLC_AGG)
    return out.dropna(subset=["Open", "High", "Low", "Close"])


def last_expected_session(now: datetime | None = None) -> date:
    """Most recent NSE session date. Ignores exchange holidays — a false
    'stale' on a holiday just triggers one cheap 5-day fetch."""
    now = now.astimezone(_IST) if now else datetime.now(_IST)
    d = now.date()
    if now.time() < dtime(9, 15):
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _normalize_daily_index(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance daily bars come tz-aware; the store's are naive. Align them."""
    df = df.copy()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index = df.index.normalize()
    return df


async def get_daily_df(ticker: str, period: str) -> pd.DataFrame:
    """Daily OHLCV for `ticker` covering `period`, store-first. Cached."""
    cache_key = f"dailydf:{ticker}:{period}"

    async def _load():
        days = PERIOD_DAYS.get(period, 380)
        df = pd.DataFrame()
        try:
            from tools import price_store
            if price_store.is_configured():
                df = await asyncio.to_thread(price_store.get_history, ticker, days)
        except Exception as e:
            log.warning("price store read failed for %s: %s", ticker, e)

        if df.empty:
            from tools.fetch_stock_data import fetch_ohlcv
            return await asyncio.to_thread(fetch_ohlcv, ticker, "1d", period)

        stale = df.index[-1].date() < last_expected_session()
        if is_market_open() or stale:
            try:
                from tools.fetch_stock_data import _fetch_yfinance
                recent = await asyncio.to_thread(_fetch_yfinance, ticker, "1d", "5d")
                recent = _normalize_daily_index(recent)
                df = pd.concat([df[~df.index.isin(recent.index)], recent]).sort_index()
            except Exception as e:
                log.warning("live top-up failed for %s: %s", ticker, e)
        return df

    return await cached(cache_key, ttl=adaptive_ttl(300), fn=_load)
