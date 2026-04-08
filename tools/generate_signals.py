"""
Generate BUY / SELL / HOLD signals from indicator-enriched DataFrames.
Score-based system: each indicator votes, total normalized to 0–100.
"""

import pandas as pd
import numpy as np


def score_rsi(rsi: float) -> tuple:
    if pd.isna(rsi):
        return 0, "No data"
    if rsi < 30:
        return 15, "Oversold — Bullish"
    if rsi < 40:
        return 8, "Approaching Oversold"
    if rsi <= 60:
        return 0, "Neutral"
    if rsi <= 70:
        return -8, "Approaching Overbought"
    return -15, "Overbought — Bearish"


def score_macd(macd: float, signal: float, prev_macd: float, prev_signal: float) -> tuple:
    if any(pd.isna(v) for v in [macd, signal, prev_macd, prev_signal]):
        return 0, "No data"
    bullish_cross = macd > signal and prev_macd <= prev_signal
    bearish_cross = macd < signal and prev_macd >= prev_signal
    if bullish_cross:
        return 20, "Bullish Crossover"
    if bearish_cross:
        return -20, "Bearish Crossover"
    if macd > signal:
        return 10, "Bullish (above signal)"
    if macd < signal:
        return -10, "Bearish (below signal)"
    return 0, "Neutral"


def score_ema_trend(price: float, ema_9, ema_21, ema_50, ema_200) -> tuple:
    def above(ema):
        return (not pd.isna(ema)) and price > ema

    count = sum([above(ema_9), above(ema_21), above(ema_50), above(ema_200)])
    valid_emas = sum([not pd.isna(e) for e in [ema_9, ema_21, ema_50, ema_200]])

    if valid_emas == 0:
        return 0, "No EMA data"

    # Normalize to available EMAs
    ratio = count / valid_emas
    if ratio == 1.0:
        return 20, f"Above all {valid_emas} EMAs — Strong Bullish"
    if ratio >= 0.75:
        return 15, "Above 3/4 EMAs — Bullish"
    if ratio >= 0.5:
        return 10, "Above 2/4 EMAs — Mildly Bullish"
    if ratio >= 0.25:
        return -10, "Below 3/4 EMAs — Mildly Bearish"
    if ratio == 0.0:
        return -20, f"Below all {valid_emas} EMAs — Strong Bearish"
    return 5, "Mixed EMA trend"


def score_bollinger(price: float, bb_upper, bb_lower, bb_middle, bb_bandwidth, prev_bb_bandwidth) -> tuple:
    if any(pd.isna(v) for v in [bb_upper, bb_lower, bb_middle]):
        return 0, "No data"

    band_range = bb_upper - bb_lower
    threshold = band_range * 0.05  # within 5% of band edge = "touching"

    if price <= bb_lower + threshold:
        return 15, "Near/At Lower Band — Oversold"
    if price >= bb_upper - threshold:
        return -15, "Near/At Upper Band — Overbought"

    # Breakout check
    if not pd.isna(prev_bb_bandwidth) and bb_bandwidth < prev_bb_bandwidth:
        return 0, "BB Squeeze — Breakout Pending"

    return 0, "Inside Bands — Neutral"


def score_support_resistance(price: float, support, resistance) -> tuple:
    proximity_pct = 0.01  # within 1% = "near"

    if support is None and resistance is None:
        return 0, "No S/R data"

    near_support = support is not None and abs(price - support) / price < proximity_pct
    near_resistance = resistance is not None and abs(price - resistance) / price < proximity_pct
    bounced_support = support is not None and 0.005 < (price - support) / price < 0.02
    broke_support = support is not None and price < support

    if near_support:
        return 15, f"Near Support {support:.2f}"
    if near_resistance:
        return -15, f"Near Resistance {resistance:.2f}"
    if bounced_support:
        return 10, f"Bounced from Support {support:.2f}"
    if broke_support:
        return -10, f"Broke Below Support {support:.2f}"
    return 0, "Between S/R levels"


def score_obv(obv_series: pd.Series, price_series: pd.Series, lookback: int = 10) -> tuple:
    if len(obv_series) < lookback or obv_series.isna().all():
        return 0, "Insufficient OBV data"

    recent_obv = obv_series.dropna().tail(lookback)
    recent_price = price_series.tail(lookback)

    obv_slope = np.polyfit(range(len(recent_obv)), recent_obv.values, 1)[0]
    price_slope = np.polyfit(range(len(recent_price)), recent_price.values, 1)[0]

    obv_rising = obv_slope > 0
    price_rising = price_slope > 0

    if obv_rising and price_rising:
        return 15, "OBV confirming uptrend"
    if not obv_rising and not price_rising:
        return -15, "OBV confirming downtrend"
    if obv_rising and not price_rising:
        return 8, "Bullish OBV divergence"
    return -8, "Bearish OBV divergence"


def generate_signal(df: pd.DataFrame, atr_multiplier: float = 1.5) -> dict:
    """
    Evaluate the latest bar of an indicator-enriched DataFrame and return a signal.

    Returns:
        dict with signal, score (0–100), last_price, stop_loss, target, components
    """
    if df.empty or len(df) < 2:
        raise ValueError("DataFrame too short — need at least 2 rows")

    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = float(last["Close"])

    support = df.attrs.get("support")
    resistance = df.attrs.get("resistance")

    # --- Score each indicator ---
    rsi_pts, rsi_label = score_rsi(last.get("RSI_14", float("nan")))

    macd_pts, macd_label = score_macd(
        last.get("MACD", float("nan")),
        last.get("MACD_signal", float("nan")),
        prev.get("MACD", float("nan")),
        prev.get("MACD_signal", float("nan")),
    )

    ema_pts, ema_label = score_ema_trend(
        price,
        last.get("EMA_9", float("nan")),
        last.get("EMA_21", float("nan")),
        last.get("EMA_50", float("nan")),
        last.get("EMA_200", float("nan")),
    )

    bb_pts, bb_label = score_bollinger(
        price,
        last.get("BB_upper", float("nan")),
        last.get("BB_lower", float("nan")),
        last.get("BB_middle", float("nan")),
        last.get("BB_bandwidth", float("nan")),
        prev.get("BB_bandwidth", float("nan")),
    )

    sr_pts, sr_label = score_support_resistance(price, support, resistance)

    obv_pts, obv_label = score_obv(df["OBV"], df["Close"])

    raw_score = rsi_pts + macd_pts + ema_pts + bb_pts + sr_pts + obv_pts
    confidence = int(((raw_score + 100) / 200) * 100)
    confidence = max(0, min(100, confidence))

    if confidence > 60:
        signal = "BUY"
    elif confidence < 40:
        signal = "SELL"
    else:
        signal = "HOLD"

    # Stop-loss and target based on ATR
    _atr_raw = last.get("ATR_14")
    try:
        atr = float(_atr_raw) if _atr_raw is not None else price * 0.02
    except (TypeError, ValueError):
        atr = price * 0.02
    if pd.isna(atr):
        atr = price * 0.02

    if signal == "BUY":
        stop_loss = round(price - atr * atr_multiplier, 2)
        target = round(price + atr * atr_multiplier * 2, 2)
    elif signal == "SELL":
        stop_loss = round(price + atr * atr_multiplier, 2)
        target = round(price - atr * atr_multiplier * 2, 2)
    else:
        stop_loss = round(price - atr * atr_multiplier, 2)
        target = round(price + atr * atr_multiplier, 2)

    return {
        "signal": signal,
        "score": confidence,
        "confidence": confidence,
        "last_price": round(price, 2),
        "stop_loss": stop_loss,
        "target": target,
        "raw_score": raw_score,
        "components": {
            "RSI":               {"value": round(float(last.get("RSI_14", float("nan"))), 2) if not pd.isna(last.get("RSI_14", float("nan"))) else "N/A", "signal": rsi_label,  "points": rsi_pts},
            "MACD":              {"value": round(float(last.get("MACD", float("nan"))), 4) if not pd.isna(last.get("MACD", float("nan"))) else "N/A",  "signal": macd_label, "points": macd_pts},
            "EMA Trend":         {"value": f"Price ₹{price:.2f}", "signal": ema_label,  "points": ema_pts},
            "Bollinger Bands":   {"value": f"BB% {round(float(last.get('BB_pct', float('nan'))), 2) if not pd.isna(last.get('BB_pct', float('nan'))) else 'N/A'}", "signal": bb_label, "points": bb_pts},
            "Support/Resistance":{"value": f"S:{support:.2f} R:{resistance:.2f}" if support and resistance else "N/A", "signal": sr_label, "points": sr_pts},
            "OBV":               {"value": "See chart", "signal": obv_label, "points": obv_pts},
        },
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from tools.fetch_stock_data import fetch_ohlcv
    from tools.compute_indicators import compute_all

    df = fetch_ohlcv("INFY.NS", interval="1d", period="1y")
    df = compute_all(df)
    sig = generate_signal(df)
    print(f"\nSignal: {sig['signal']}  |  Confidence: {sig['confidence']}%  |  Price: ₹{sig['last_price']}")
    print(f"Stop Loss: ₹{sig['stop_loss']}  |  Target: ₹{sig['target']}")
    print("\nIndicator Breakdown:")
    for name, v in sig["components"].items():
        print(f"  {name:20s}  {str(v['value']):30s}  {v['signal']:35s}  {v['points']:+d} pts")
