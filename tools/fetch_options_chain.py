"""
Fetch live NSE options chain for index symbols (NIFTY, BANKNIFTY, MIDCPNIFTY).
Uses Angel One SmartAPI — real-time OI, LTP, volume, bid/ask.
Returns the same dict shape as the previous NSE-scraping version so all
downstream code (analyze_options.py, index_options.py) continues to work
with zero changes.
"""

import time
import threading
import requests
import pandas as pd
from datetime import datetime

from tools.angel_auth import get_session, reset_session

# ── Tool-level result cache ────────────────────────────────────────────────────
# Caches fetch_options_chain() results for 55s so the double-call inside
# recommend_option() (near_expiry + next_expiry) doesn't hit Angel One twice.
_chain_cache: dict = {}   # key -> (result, expires_at)
_chain_lock = threading.Lock()
_CHAIN_TTL = 55           # seconds

# ── Constants ──────────────────────────────────────────────────────────────────

INDEX_SYMBOLS = ["NIFTY", "BANKNIFTY", "MIDCPNIFTY"]

LOT_SIZES = {
    "NIFTY":      75,
    "BANKNIFTY":  30,
    "MIDCPNIFTY": 120,
}

STRIKE_INTERVALS = {
    "NIFTY":      50,
    "BANKNIFTY":  100,
    "MIDCPNIFTY": 25,
}

YFINANCE_TICKERS = {
    "NIFTY":      "^NSEI",
    "BANKNIFTY":  "^NSEBANK",
    "MIDCPNIFTY": "^NSEMDCP50",
}

STRIKES_EACH_SIDE = 15   # strikes either side of ATM
BATCH_SIZE = 50          # Angel One getMarketData limit per call
MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

# ── Instrument master cache ────────────────────────────────────────────────────

_master_cache: list | None = None
_master_fetched_at: float = 0.0
MASTER_TTL = 3600  # 1 hour


def _get_master() -> list:
    global _master_cache, _master_fetched_at
    now = time.time()
    if _master_cache is None or (now - _master_fetched_at) > MASTER_TTL:
        resp = requests.get(MASTER_URL, timeout=60)
        resp.raise_for_status()
        _master_cache = resp.json()
        _master_fetched_at = now
    return _master_cache


def _get_option_tokens(symbol: str) -> list[dict]:
    """Return all NFO option contracts for the given index symbol."""
    master = _get_master()
    rows = []
    for item in master:
        if (
            item.get("exch_seg") == "NFO"
            and item.get("name") == symbol
            and item.get("instrumenttype") == "OPTIDX"
        ):
            raw_strike = float(item.get("strike", 0))
            strike = int(raw_strike / 100)  # Angel One stores strike * 100
            opt_type = "CE" if item["symbol"].endswith("CE") else "PE"
            rows.append({
                "token":       item["token"],
                "symbol":      item["symbol"],
                "name":        symbol,
                "expiry":      item["expiry"],   # e.g. "07APR2026"
                "strike":      strike,
                "option_type": opt_type,
                "lot_size":    int(item.get("lotsize", LOT_SIZES.get(symbol, 75))),
            })
    return rows


def _get_sorted_expiries(tokens: list[dict]) -> list[str]:
    """Return expiry strings sorted chronologically."""
    raw = sorted(set(t["expiry"] for t in tokens))
    parsed = []
    for e in raw:
        try:
            parsed.append((datetime.strptime(e, "%d%b%Y"), e))
        except ValueError:
            pass
    parsed.sort()
    return [e for _, e in parsed]


def _get_spot(symbol: str) -> float:
    """Get live index spot price via Angel One ltpData."""
    spot_tokens = {
        "NIFTY":      ("NSE", "Nifty 50",          "99926000"),
        "BANKNIFTY":  ("NSE", "Nifty Bank",         "99926009"),
        "MIDCPNIFTY": ("NSE", "NIFTY MID SELECT",   "99926074"),
    }
    exch, name, token = spot_tokens.get(symbol, ("NSE", "Nifty 50", "99926000"))
    obj = get_session()
    resp = obj.ltpData(exch, name, token)
    if resp and resp.get("status") and resp.get("data"):
        return float(resp["data"]["ltp"])
    raise ValueError(f"Could not fetch spot price for {symbol}: {resp}")


def _get_market_data(tokens: list[str]) -> dict:
    """
    Fetch FULL market data for a list of NFO tokens.
    Returns {token: data_dict}. Handles batching + token-expiry retry.
    """
    obj = get_session()
    result = {}
    for i in range(0, len(tokens), BATCH_SIZE):
        batch = tokens[i: i + BATCH_SIZE]
        try:
            resp = obj.getMarketData("FULL", {"NFO": batch})
        except Exception:
            reset_session()
            obj = get_session()
            resp = obj.getMarketData("FULL", {"NFO": batch})
        if resp and resp.get("status") and resp.get("data"):
            for item in resp["data"].get("fetched", []):
                result[item["symbolToken"]] = item
        if i + BATCH_SIZE < len(tokens):
            time.sleep(0.3)
    return result


def _parse_bid_ask(depth: dict) -> tuple[float, float]:
    bid, ask = 0.0, 0.0
    try:
        buys = depth.get("buy", [])
        if buys:
            bid = float(buys[0].get("price", 0) or 0)
    except Exception:
        pass
    try:
        sells = depth.get("sell", [])
        if sells:
            ask = float(sells[0].get("price", 0) or 0)
    except Exception:
        pass
    return bid, ask


# ── Main public function ───────────────────────────────────────────────────────

def _fetch_options_chain_uncached(symbol: str, expiry: str = None) -> dict:
    """
    Fetch live options chain for an index symbol.

    Returns:
        {
            "symbol":           str,
            "underlying_value": float,
            "timestamp":        str,
            "expiry_dates":     list[str],
            "chain":            pd.DataFrame
        }

    DataFrame columns:
        strike, expiry,
        CE_ltp, CE_oi, CE_chg_oi, CE_iv, CE_volume, CE_bid, CE_ask,
        PE_ltp, PE_oi, PE_chg_oi, PE_iv, PE_volume, PE_bid, PE_ask
    """
    if symbol not in INDEX_SYMBOLS:
        raise ValueError(f"Symbol must be one of {INDEX_SYMBOLS}")

    spot = _get_spot(symbol)
    all_tokens = _get_option_tokens(symbol)
    if not all_tokens:
        raise ValueError(f"No options data found for {symbol} in instrument master.")

    expiry_dates = _get_sorted_expiries(all_tokens)
    if not expiry_dates:
        raise ValueError(f"No options data returned for {symbol}.")

    target_expiry = expiry if expiry and expiry in expiry_dates else expiry_dates[0]

    interval = STRIKE_INTERVALS.get(symbol, 50)
    atm = get_nearest_atm_strike(spot, symbol)
    lo = atm - interval * STRIKES_EACH_SIDE
    hi = atm + interval * STRIKES_EACH_SIDE

    relevant = [
        t for t in all_tokens
        if t["expiry"] == target_expiry and lo <= t["strike"] <= hi
    ]
    if not relevant:
        relevant = [t for t in all_tokens if t["expiry"] == target_expiry]

    token_ids = [t["token"] for t in relevant]
    token_map = {t["token"]: t for t in relevant}

    mkt = _get_market_data(token_ids)

    ce_data: dict[int, dict] = {}
    pe_data: dict[int, dict] = {}

    def _empty():
        return {"ltp": 0.0, "oi": 0, "chg_oi": 0, "iv": 0.0, "volume": 0, "bid": 0.0, "ask": 0.0}

    for token_id, info in token_map.items():
        m = mkt.get(token_id, {})
        strike = info["strike"]
        bid, ask = _parse_bid_ask(m.get("depth", {}))
        row = {
            "ltp":    float(m.get("ltp", 0) or 0),
            "oi":     int(m.get("opnInterest", 0) or 0),
            "chg_oi": 0,
            "iv":     0.0,
            "volume": int(m.get("tradeVolume", 0) or 0),
            "bid":    bid,
            "ask":    ask,
        }
        if info["option_type"] == "CE":
            ce_data[strike] = row
        else:
            pe_data[strike] = row

    all_strikes = sorted(set(ce_data) | set(pe_data))
    rows = []
    for strike in all_strikes:
        ce = ce_data.get(strike, _empty())
        pe = pe_data.get(strike, _empty())
        rows.append({
            "strike":    strike,
            "expiry":    target_expiry,
            "CE_ltp":    ce["ltp"],  "CE_oi":    ce["oi"],  "CE_chg_oi": ce["chg_oi"],
            "CE_iv":     ce["iv"],   "CE_volume": ce["volume"], "CE_bid": ce["bid"], "CE_ask": ce["ask"],
            "PE_ltp":    pe["ltp"],  "PE_oi":    pe["oi"],  "PE_chg_oi": pe["chg_oi"],
            "PE_iv":     pe["iv"],   "PE_volume": pe["volume"], "PE_bid": pe["bid"], "PE_ask": pe["ask"],
        })

    chain_df = pd.DataFrame(rows)

    return {
        "symbol":           symbol,
        "underlying_value": spot,
        "timestamp":        datetime.now().strftime("%H:%M:%S"),
        "expiry_dates":     expiry_dates,
        "chain":            chain_df,
    }


def fetch_options_chain(symbol: str, expiry: str = None) -> dict:
    """Cached wrapper around _fetch_options_chain_uncached. TTL = 55s."""
    key = f"{symbol}:{expiry or 'nearest'}"
    now = time.time()
    with _chain_lock:
        entry = _chain_cache.get(key)
        if entry is not None and entry[1] > now:
            return entry[0]
    result = _fetch_options_chain_uncached(symbol, expiry)
    with _chain_lock:
        _chain_cache[key] = (result, now + _CHAIN_TTL)
    return result


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_nearest_atm_strike(spot: float, symbol: str) -> int:
    interval = STRIKE_INTERVALS.get(symbol, 50)
    return round(spot / interval) * interval


def get_expiry_options(expiry_dates: list[str], style: str = "both") -> tuple:
    if not expiry_dates:
        return None, None
    near = expiry_dates[0]
    nxt  = expiry_dates[1] if len(expiry_dates) > 1 else near
    return near, nxt


if __name__ == "__main__":
    print("Fetching NIFTY option chain...")
    data = fetch_options_chain("NIFTY")
    print(f"Spot:    {data['underlying_value']}")
    print(f"Expiries: {data['expiry_dates'][:4]}")
    print(f"Rows:    {len(data['chain'])}")
    print(data["chain"].head(6).to_string())
