"""
Compute technical indicators on OHLCV DataFrames.
All functions are stateless — no I/O, no network calls.
Implemented with pure pandas/numpy (no pandas-ta dependency).
"""

import pandas as pd
import numpy as np


def compute_emas(df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
    if periods is None:
        periods = [9, 21, 50, 200]
    for p in periods:
        df[f"EMA_{p}"] = df["Close"].ewm(span=p, adjust=False).mean()
    return df


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df[f"RSI_{period}"] = 100 - (100 / (1 + rs))
    return df


def compute_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    df["MACD"] = macd_line
    df["MACD_signal"] = signal_line
    df["MACD_hist"] = macd_line - signal_line
    return df


def compute_bollinger(
    df: pd.DataFrame, period: int = 20, std: float = 2.0
) -> pd.DataFrame:
    middle = df["Close"].rolling(window=period).mean()
    rolling_std = df["Close"].rolling(window=period).std(ddof=0)
    upper = middle + std * rolling_std
    lower = middle - std * rolling_std
    df["BB_lower"] = lower
    df["BB_middle"] = middle
    df["BB_upper"] = upper
    df["BB_bandwidth"] = (upper - lower) / middle
    df["BB_pct"] = (df["Close"] - lower) / (upper - lower)
    return df


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df[f"ATR_{period}"] = tr.ewm(alpha=1 / period, adjust=False).mean()
    return df


def compute_obv(df: pd.DataFrame) -> pd.DataFrame:
    direction = np.sign(df["Close"].diff()).fillna(0)
    df["OBV"] = (direction * df["Volume"]).cumsum()
    return df


def compute_support_resistance(
    df: pd.DataFrame, lookback: int = 50, swing_window: int = 5
) -> tuple:
    """
    Detect support and resistance levels using swing highs/lows.

    Returns:
        (support_level, resistance_level) — nearest levels to current price.
        Returns (None, None) if insufficient data.
    """
    if len(df) < swing_window * 2 + 1:
        return None, None

    recent = df.tail(lookback).copy()
    highs = recent["High"].values
    lows = recent["Low"].values
    current_price = df["Close"].iloc[-1]

    swing_highs = []
    swing_lows = []
    w = swing_window

    for i in range(w, len(recent) - w):
        if highs[i] == max(highs[i - w: i + w + 1]):
            swing_highs.append(highs[i])
        if lows[i] == min(lows[i - w: i + w + 1]):
            swing_lows.append(lows[i])

    def cluster_levels(levels: list, threshold_pct: float = 0.005) -> list:
        """Group nearby levels and return the most-touched ones."""
        if not levels:
            return []
        levels = sorted(levels)
        clusters = [[levels[0]]]
        for lvl in levels[1:]:
            if abs(lvl - clusters[-1][-1]) / clusters[-1][-1] < threshold_pct:
                clusters[-1].append(lvl)
            else:
                clusters.append([lvl])
        return [np.mean(c) for c in clusters]

    resistance_levels = cluster_levels(swing_highs)
    support_levels = cluster_levels(swing_lows)

    resistances_above = [r for r in resistance_levels if r > current_price]
    resistance = min(resistances_above) if resistances_above else (
        max(resistance_levels) if resistance_levels else None
    )

    supports_below = [s for s in support_levels if s < current_price]
    support = max(supports_below) if supports_below else (
        min(support_levels) if support_levels else None
    )

    return support, resistance


def compute_all(
    df: pd.DataFrame,
    ema_periods: list = None,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    bb_period: int = 20,
    bb_std: float = 2.0,
    atr_period: int = 14,
) -> pd.DataFrame:
    """
    Compute all indicators and return enriched DataFrame.
    Support/Resistance levels are stored as scalar attributes on the DataFrame.
    """
    if ema_periods is None:
        ema_periods = [9, 21, 50, 200]

    df = df.copy()
    df = compute_emas(df, ema_periods)
    df = compute_rsi(df, rsi_period)
    df = compute_macd(df, macd_fast, macd_slow, macd_signal)
    df = compute_bollinger(df, bb_period, bb_std)
    df = compute_atr(df, atr_period)
    df = compute_obv(df)

    support, resistance = compute_support_resistance(df)
    df.attrs["support"] = support
    df.attrs["resistance"] = resistance

    return df


if __name__ == "__main__":
    from tools.fetch_stock_data import fetch_ohlcv
    df = fetch_ohlcv("TCS.NS", interval="1d", period="1y")
    df = compute_all(df)
    print("Columns:", df.columns.tolist())
    print(df[["Close", "RSI_14", "MACD", "EMA_50"]].tail(3))
    print(f"Support: {df.attrs['support']:.2f}, Resistance: {df.attrs['resistance']:.2f}")
