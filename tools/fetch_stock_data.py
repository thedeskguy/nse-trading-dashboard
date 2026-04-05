"""
Fetch real OHLCV data from Yahoo Finance for NSE/BSE stocks.
Uses yfinance — no API key required.
"""

import yfinance as yf
import pandas as pd

VALID_COMBOS = {
    "5m":  ["1d", "5d", "1mo"],
    "15m": ["1d", "5d", "1mo", "3mo"],
    "30m": ["1d", "5d", "1mo", "3mo"],
    "1h":  ["1d", "5d", "1mo", "3mo", "6mo"],
    "1d":  ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
    "1wk": ["3mo", "6mo", "1y", "2y", "5y"],
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


def fetch_ohlcv(
    ticker: str,
    interval: str = "1d",
    period: str = "3mo",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """
    Fetch OHLCV data for a ticker.

    Args:
        ticker:       Yahoo Finance ticker (e.g. 'RELIANCE.NS', 'TCS.NS')
        interval:     One of: 5m, 15m, 30m, 1h, 1d, 1wk
        period:       Lookback period (must be valid for the interval)
        auto_adjust:  Adjust for splits/dividends

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
        Index: DatetimeIndex

    Raises:
        ValueError: Invalid interval/period combo or empty response
    """
    if interval not in VALID_COMBOS:
        raise ValueError(f"Invalid interval '{interval}'. Choose from: {list(VALID_COMBOS)}")

    if period not in VALID_COMBOS[interval]:
        raise ValueError(
            f"Period '{period}' not valid for interval '{interval}'. "
            f"Valid periods: {VALID_COMBOS[interval]}"
        )

    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval, auto_adjust=auto_adjust)

    if df.empty:
        raise ValueError(
            f"No data returned for '{ticker}'. "
            "Check that the ticker is correct and the market has trading history."
        )

    # Keep only standard OHLCV columns
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()

    # Convert intraday index to IST
    if interval in ("5m", "15m", "30m", "1h"):
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df.index = df.index.tz_convert("Asia/Kolkata")

    df = validate_dataframe(df)

    if df.empty:
        raise ValueError(f"Data for '{ticker}' was empty after cleaning.")

    return df


if __name__ == "__main__":
    df = fetch_ohlcv("RELIANCE.NS", interval="1d", period="3mo")
    print(f"Fetched {len(df)} rows for RELIANCE.NS")
    print(df.tail(3))
