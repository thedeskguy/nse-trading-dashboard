"""
Fetch OHLCV data for NSE/BSE stocks.
Primary: Angel One SmartAPI (real-time, no delay) — requires .env credentials.
Fallback: Yahoo Finance (free, ~15 min delay for intraday).
"""

import yfinance as yf
import pandas as pd

VALID_COMBOS = {
    "1m":  ["1d", "5d"],
    "5m":  ["1d", "5d", "1mo"],
    "15m": ["1d", "5d", "1mo", "3mo"],
    "30m": ["1d", "5d", "1mo", "3mo"],
    "1h":  ["1d", "5d", "1mo", "3mo", "6mo"],
    "1d":  ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
    "1wk": ["3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
    "1mo": ["1y", "2y", "5y", "10y", "max"],
}


def resolve_ticker(symbol: str, exchange: str = "NSE") -> str:
    """Convert plain symbol to Yahoo Finance format."""
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO") or symbol.startswith("^"):
        return symbol
    suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
    return symbol + suffix


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean up raw yfinance output."""
    if df.empty:
        return df
    # Drop rows with any NaN in OHLCV
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    # Drop zero-volume rows (common in BSE .BO data)
    df = df[df["Volume"] > 0]
    # Drop duplicate index entries (yfinance occasionally duplicates last row)
    df = df[~df.index.duplicated(keep="last")]
    # Ensure ascending order
    df = df.sort_index()
    return df


def _fetch_yfinance(ticker: str, interval: str, period: str, auto_adjust: bool = True) -> pd.DataFrame:
    """Raw yfinance fetch — raises ValueError on failure or when circuit is open."""
    try:
        from services.circuit_breaker import yfinance_breaker
        _breaker = yfinance_breaker
    except ImportError:
        _breaker = None

    if _breaker and _breaker.is_open():
        raise ValueError(
            f"yfinance circuit is open after repeated 429/failures — "
            f"retry in ~{_breaker.cooldown_seconds}s."
        )

    yf_symbol = resolve_ticker(ticker)
    t = yf.Ticker(yf_symbol)

    try:
        df = t.history(period=period, interval=interval, auto_adjust=auto_adjust)
    except Exception as exc:
        # yfinance raises generic exceptions for HTTP 429 and other errors.
        msg = str(exc).lower()
        if "429" in msg or "too many requests" in msg or "rate limit" in msg:
            if _breaker:
                _breaker.record_failure()
        raise ValueError(f"yfinance error for '{ticker}': {exc}") from exc

    if df.empty:
        # An empty response for a valid ticker usually means a 429-throttle with no exception.
        if _breaker:
            _breaker.record_failure()
        raise ValueError(
            f"No data returned for '{ticker}'. "
            "Check that the ticker is correct and the market has trading history."
        )

    if _breaker:
        _breaker.record_success()

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()

    if interval in ("1m", "5m", "15m", "30m", "1h"):
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df.index = df.index.tz_convert("Asia/Kolkata")

    df = validate_dataframe(df)

    if df.empty:
        raise ValueError(f"Data for '{ticker}' was empty after cleaning.")

    return df


def fetch_ohlcv(
    ticker: str,
    interval: str = "1d",
    period: str = "3mo",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """
    Fetch OHLCV data for a ticker.

    Tries Angel One SmartAPI first (real-time). Falls back to Yahoo Finance
    if credentials are missing, the symbol isn't in the master, or any error occurs.

    Args:
        ticker:   Yahoo Finance ticker format (e.g. 'RELIANCE.NS', '^NSEI')
        interval: One of: 5m, 15m, 30m, 1h, 1d, 1wk
        period:   Lookback period (must be valid for the interval)

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume (DatetimeIndex)

    Raises:
        ValueError: if both sources fail or interval/period is invalid
    """
    if interval not in VALID_COMBOS:
        raise ValueError(f"Invalid interval '{interval}'. Choose from: {list(VALID_COMBOS)}")

    if period not in VALID_COMBOS[interval]:
        raise ValueError(
            f"Period '{period}' not valid for interval '{interval}'. "
            f"Valid periods: {VALID_COMBOS[interval]}"
        )

    # Angel One has ~3-month history. For long periods, go straight to yfinance.
    _ANGEL_OK_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo"}
    _skip_angel = period not in _ANGEL_OK_PERIODS

    # ── Try Angel One first (5-second hard timeout) ────────────────────────────
    if not _skip_angel:
        import concurrent.futures
        try:
            from tools.fetch_angel_ohlcv import fetch_angel_ohlcv
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(fetch_angel_ohlcv, ticker, interval, period)
                try:
                    df = future.result(timeout=5)
                    if df is not None and not df.empty:
                        return df
                except concurrent.futures.TimeoutError:
                    pass  # Angel One too slow — fall back immediately
        except Exception:
            pass

    # ── Fallback: Yahoo Finance ────────────────────────────────────────────────
    return _fetch_yfinance(ticker, interval, period, auto_adjust)


if __name__ == "__main__":
    df = fetch_ohlcv("RELIANCE.NS", interval="1d", period="3mo")
    print(f"Fetched {len(df)} rows for RELIANCE.NS")
    print(df.tail(3))
