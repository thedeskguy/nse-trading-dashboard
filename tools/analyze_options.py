"""
Recommend which Call or Put to BUY for index options.
Only buy-side recommendations (no selling, no futures).
Uses underlying trend signal + options chain data to pick the right strike & expiry.
"""

import pandas as pd
import numpy as np
from tools.fetch_options_chain import (
    fetch_options_chain,
    get_nearest_atm_strike,
    get_expiry_options,
    LOT_SIZES,
    STRIKE_INTERVALS,
    YFINANCE_TICKERS,
)
from tools.fetch_stock_data import fetch_ohlcv
from tools.compute_indicators import compute_all
from tools.generate_signals import generate_signal


# ── Strike selection ──────────────────────────────────────────────────────────

def select_strike(
    spot: float,
    signal: str,
    confidence: int,
    symbol: str,
    option_type: str,   # "CE" or "PE"
    style: str = "intraday",
) -> int:
    """
    Pick the best strike to buy.

    Logic:
    - Strong signal (confidence >= 70): ATM (maximum delta, fastest mover)
    - Moderate signal (60–70):          1 strike OTM (cheaper, still good delta)
    - Intraday: bias ATM (time decay aggressive OTM intraday)
    - Positional: can go 1 OTM for better R/R on premium
    """
    interval = STRIKE_INTERVALS.get(symbol, 50)
    atm = get_nearest_atm_strike(spot, symbol)

    if style == "intraday":
        # Always ATM for intraday — theta kills OTM options fast
        return atm
    else:
        # Positional: ATM for strong, 1 OTM for moderate
        if confidence >= 70:
            return atm
        else:
            if option_type == "CE":
                return atm + interval   # 1 OTM call
            else:
                return atm - interval   # 1 OTM put


def get_option_premium(chain_df: pd.DataFrame, strike: int, expiry: str, option_type: str) -> dict:
    """
    Extract premium info for a specific strike + expiry + type from the chain DataFrame.
    Returns dict with ltp, iv, oi, volume, bid, ask.
    """
    mask = (chain_df["strike"] == strike) & (chain_df["expiry"] == expiry)
    rows = chain_df[mask]

    if rows.empty:
        # Find nearest available strike
        available = chain_df[chain_df["expiry"] == expiry]["strike"].values
        if len(available) == 0:
            return {}
        nearest = available[np.argmin(np.abs(available - strike))]
        rows = chain_df[(chain_df["strike"] == nearest) & (chain_df["expiry"] == expiry)]
        strike = nearest

    row = rows.iloc[0]
    prefix = option_type  # "CE" or "PE"
    return {
        "strike":  strike,
        "ltp":     float(row[f"{prefix}_ltp"]),
        "iv":      float(row[f"{prefix}_iv"]),
        "oi":      int(row[f"{prefix}_oi"]),
        "volume":  int(row[f"{prefix}_volume"]),
        "bid":     float(row[f"{prefix}_bid"]),
        "ask":     float(row[f"{prefix}_ask"]),
    }


# ── SL / Target on premium ────────────────────────────────────────────────────

def compute_option_sl_target(
    premium: float,
    signal_confidence: int,
    style: str = "intraday",
) -> tuple:
    """
    Compute stop-loss and target on the premium itself.

    Intraday:
    - SL:     35% of premium (exit if premium falls to 65% of entry)
    - Target: 70–80% gain on premium

    Positional:
    - SL:     40% of premium
    - Target: 100% gain (double the premium)

    Returns (stop_loss_premium, target_premium, sl_pct, target_pct)
    """
    if style == "intraday":
        sl_pct = 0.35
        target_pct = 0.75 if signal_confidence >= 70 else 0.65
    else:
        sl_pct = 0.40
        target_pct = 1.00 if signal_confidence >= 70 else 0.80

    sl_price = round(premium * (1 - sl_pct), 2)
    target_price = round(premium * (1 + target_pct), 2)

    return sl_price, target_price, sl_pct, target_pct


# ── PCR Analysis ──────────────────────────────────────────────────────────────

def compute_pcr(chain_df: pd.DataFrame, expiry: str = None) -> dict:
    """
    Compute Put-Call Ratio (OI-based) — key sentiment indicator for indices.

    PCR > 1.2  → Bullish (more puts being written = market expects upside)
    PCR < 0.8  → Bearish (more calls being written = market expects downside)
    PCR 0.8–1.2 → Neutral
    """
    df = chain_df[chain_df["expiry"] == expiry] if expiry else chain_df
    total_put_oi = df["PE_oi"].sum()
    total_call_oi = df["CE_oi"].sum()

    if total_call_oi == 0:
        return {"pcr": None, "signal": "No data"}

    pcr = round(total_put_oi / total_call_oi, 3)

    if pcr > 1.2:
        pcr_signal = "Bullish (high put writing)"
    elif pcr < 0.8:
        pcr_signal = "Bearish (high call writing)"
    else:
        pcr_signal = "Neutral"

    return {"pcr": pcr, "signal": pcr_signal}


def find_max_pain(chain_df: pd.DataFrame, expiry: str) -> float:
    """
    Find the Max Pain strike — the price at which option buyers lose the most.
    Market tends to gravitate toward max pain near expiry.
    """
    df = chain_df[chain_df["expiry"] == expiry].copy()
    if df.empty:
        return None

    strikes = df["strike"].values
    total_loss = []

    for target_strike in strikes:
        # ITM calls lose: sum of (strike - target_strike) * CE_oi for all strikes < target_strike
        call_loss = sum(
            max(0, s - target_strike) * oi
            for s, oi in zip(df["strike"], df["CE_oi"])
        )
        # ITM puts lose: sum of (target_strike - strike) * PE_oi for all strikes > target_strike
        put_loss = sum(
            max(0, target_strike - s) * oi
            for s, oi in zip(df["strike"], df["PE_oi"])
        )
        total_loss.append(call_loss + put_loss)

    max_pain_idx = int(np.argmin(total_loss))
    return float(strikes[max_pain_idx])


# ── Main recommendation engine ────────────────────────────────────────────────

def recommend_option(symbol: str, style: str = "both", expiry: str = None) -> dict:
    """
    Full pipeline: fetch index data → compute signal → fetch options chain
    → recommend which Call or Put to buy.

    Args:
        symbol: NIFTY, BANKNIFTY, or MIDCPNIFTY
        style:  'intraday', 'positional', or 'both'
        expiry: If provided, use this as the base expiry for intraday;
                next available expiry after it is used for positional.
                If None, defaults to nearest expiry.

    Returns:
        dict with full recommendation for intraday and/or positional
    """
    symbol = symbol.upper()

    # Step 1: Get underlying trend signal
    yf_ticker = YFINANCE_TICKERS[symbol]
    df_index = fetch_ohlcv(yf_ticker, interval="1d", period="1y")
    df_index = compute_all(df_index)
    sig = generate_signal(df_index)

    underlying_signal = sig["signal"]      # BUY, SELL, or HOLD
    confidence = sig["confidence"]
    spot = sig["last_price"]

    # HOLD → no options trade
    if underlying_signal == "HOLD":
        return {
            "symbol": symbol,
            "spot": spot,
            "underlying_signal": "HOLD",
            "confidence": confidence,
            "recommendation": None,
            "message": "No options trade recommended — underlying trend is HOLD (conflicting signals).",
        }

    # Map underlying signal to option type
    option_type = "CE" if underlying_signal == "BUY" else "PE"
    option_label = "CALL" if option_type == "CE" else "PUT"

    # Step 2: Resolve expiry dates (fetch without filter to get full list cheaply)
    chain_meta = fetch_options_chain(symbol)
    expiry_dates = chain_meta["expiry_dates"]
    nse_spot = chain_meta["underlying_value"] or spot

    if expiry and expiry in expiry_dates:
        near_expiry = expiry
        idx = expiry_dates.index(expiry)
        next_expiry = expiry_dates[idx + 1] if idx + 1 < len(expiry_dates) else expiry
    else:
        near_expiry, next_expiry = get_expiry_options(expiry_dates)

    # Fetch chain for near_expiry specifically (may differ from expiry_dates[0])
    if near_expiry != expiry_dates[0]:
        chain_near = fetch_options_chain(symbol, expiry=near_expiry)
    else:
        chain_near = chain_meta  # already fetched above

    chain_df = chain_near["chain"]

    # Fetch next_expiry data and merge so positional tab always has data
    if next_expiry and next_expiry != near_expiry:
        chain_next = fetch_options_chain(symbol, expiry=next_expiry)
        chain_df = pd.concat([chain_df, chain_next["chain"]], ignore_index=True)

    # Step 3: PCR and Max Pain
    pcr_data = compute_pcr(chain_df, near_expiry)
    max_pain = find_max_pain(chain_df, near_expiry) if near_expiry else None

    # Step 4: Build recommendations
    styles_to_build = ["intraday", "positional"] if style == "both" else [style]
    recommendations = {}

    for s in styles_to_build:
        exp = near_expiry if s == "intraday" else next_expiry
        if not exp:
            continue

        strike = select_strike(nse_spot, underlying_signal, confidence, symbol, option_type, s)
        prem_info = get_option_premium(chain_df, strike, exp, option_type)

        if not prem_info or prem_info.get("ltp", 0) == 0:
            recommendations[s] = {"error": f"No premium data for {symbol} {strike} {option_type} {exp}"}
            continue

        premium = prem_info["ltp"]
        lot_size = LOT_SIZES[symbol]
        capital = round(premium * lot_size, 2)
        sl, target, sl_pct, tgt_pct = compute_option_sl_target(premium, confidence, s)

        recommendations[s] = {
            "option":         f"{symbol} {strike} {option_type} ({exp})",
            "option_type":    option_label,
            "strike":         strike,
            "expiry":         exp,
            "premium":        premium,
            "bid":            prem_info.get("bid", 0),
            "ask":            prem_info.get("ask", 0),
            "iv":             prem_info.get("iv", 0),
            "oi":             prem_info.get("oi", 0),
            "lot_size":       lot_size,
            "capital_1_lot":  capital,
            "stop_loss":      sl,
            "target":         target,
            "sl_pct":         int(sl_pct * 100),
            "target_pct":     int(tgt_pct * 100),
            "sl_points":      round(premium - sl, 2),
            "target_points":  round(target - premium, 2),
            "max_loss_1_lot": round((premium - sl) * lot_size, 2),
            "max_profit_1_lot": round((target - premium) * lot_size, 2),
        }

    return {
        "symbol":            symbol,
        "spot":              round(nse_spot, 2),
        "timestamp":         chain_near["timestamp"],
        "underlying_signal": underlying_signal,
        "confidence":        confidence,
        "option_type":       option_label,
        "pcr":               pcr_data,
        "max_pain":          max_pain,
        "expiry_dates":      expiry_dates,
        "selected_expiry":   near_expiry,
        "signal_components": sig["components"],
        "recommendations":   recommendations,
        "message":           f"Trend is {underlying_signal} ({confidence}% confidence) → Buy {option_label}",
    }


if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "NIFTY"
    print(f"\nAnalyzing {symbol} options...\n")
    result = recommend_option(symbol, style="both")
    print(f"Spot:   ₹{result['spot']:,.2f}")
    print(f"Signal: {result['underlying_signal']} ({result['confidence']}% confidence)")
    print(f"Action: Buy {result.get('option_type', 'N/A')}")
    print(f"PCR:    {result['pcr']}")
    print(f"Max Pain: {result.get('max_pain')}")
    print()
    for style, rec in result.get("recommendations", {}).items():
        if "error" in rec:
            print(f"[{style.upper()}] Error: {rec['error']}")
            continue
        print(f"[{style.upper()}]")
        print(f"  Option:       {rec['option']}")
        print(f"  Premium:      ₹{rec['premium']}")
        print(f"  Stop Loss:    ₹{rec['stop_loss']}  (-{rec['sl_pct']}% | -{rec['sl_points']} pts)")
        print(f"  Target:       ₹{rec['target']}  (+{rec['target_pct']}% | +{rec['target_points']} pts)")
        print(f"  Lot Size:     {rec['lot_size']}")
        print(f"  Capital/lot:  ₹{rec['capital_1_lot']:,.2f}")
        print(f"  Max Loss/lot: ₹{rec['max_loss_1_lot']:,.2f}")
        print(f"  Max P&L/lot:  ₹{rec['max_profit_1_lot']:,.2f}")
        print()
