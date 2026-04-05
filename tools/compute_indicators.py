"""
Compute technical indicators on OHLCV DataFrames.
All functions are stateless — no I/O, no network calls.
Uses pandas-ta with explicit Series assignment (pandas 2.x compatible).
"""

import pandas as pd
import numpy as np
import pandas_ta as ta


def compute_emas(df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
    if periods is None:
        periods = [9, 21, 50, 200]
    for p in periods:
        df[f"EMA_{p}"] = ta.ema(df["Close"], length=p)
    return df


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df[f"RSI_{period}"] = ta.rsi(df["Close"], length=period)
    return df


def compute_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    macd_df = ta.macd(df["Close"], fast=fast, slow=slow, signal=signal)
    if macd_df is not None and not macd_df.empty:
        # pandas-ta names: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        col_map = {
            macd_df.columns[0]: "MACD",
            macd_df.columns[1]: "MACD_hist",
            macd_df.columns[2]: "MACD_signal",
        }
        macd_df = macd_df.rename(columns=col_map)
        df["MACD"] = macd_df["MACD"]
        df["MACD_signal"] = macd_df["MACD_signal"]
        df["MACD_hist"] = macd_df["MACD_hist"]
    return df


def compute_bollinger(
    df: pd.DataFrame, period: int = 20, std: float = 2.0
) -> pd.DataFrame:
    bb = ta.bbands(df["Close"], length=period, std=std)
    if bb is not None and not bb.empty:
        # pandas-ta names: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0
        df["BB_lower"] = bb.iloc[:, 0]
        df["BB_middle"] = bb.iloc[:, 1]
        df["BB_upper"] = bb.iloc[:, 2]
        df["BB_bandwidth"] = bb.iloc[:, 3]
        df["BB_pct"] = bb.iloc[:, 4]
    return df


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df[f"ATR_{period}"] = ta.atr(df["High"], df["Low"], df["Close"], length=period)
    return df


def compute_obv(df: pd.DataFrame) -> pd.DataFrame:
    df["OBV"] = ta.obv(df["Close"], df["Volume"])
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
        # Return representative level (mean) of each cluster
        return [np.mean(c) for c in clusters]

    resistance_levels = cluster_levels(swing_highs)
    support_levels = cluster_levels(swing_lows)

    # Nearest resistance above current price
    resistances_above = [r for r in resistance_levels if r > current_price]
    resistance = min(resistances_above) if resistances_above else (
        max(resistance_levels) if resistance_levels else None
    )

    # Nearest support below current price
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
    # Attach as metadata
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
