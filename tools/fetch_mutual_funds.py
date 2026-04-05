"""
Indian Mutual Fund data fetcher using mfapi.in (free, no API key).
Endpoints:
  GET https://api.mfapi.in/mf               → all schemes
  GET https://api.mfapi.in/mf/{scheme_code} → NAV history
  GET https://api.mfapi.in/mf/search?q=...  → search by name
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

MFAPI_BASE = "https://api.mfapi.in/mf"

# ── Curated popular Indian MFs (Direct Growth plans) ─────────────────────────
# Scheme codes sourced from mfapi.in — all are Direct Plan - Growth variants
POPULAR_FUNDS: dict[str, list[dict]] = {
    "Large Cap": [
        {"name": "Mirae Asset Large Cap",          "scheme_code": 118834},
        {"name": "Axis Bluechip",                  "scheme_code": 120503},
        {"name": "HDFC Top 100",                   "scheme_code": 100339},
        {"name": "ICICI Pru Bluechip",             "scheme_code": 120578},
        {"name": "SBI Bluechip",                   "scheme_code": 119598},
        {"name": "Kotak Bluechip",                 "scheme_code": 120586},
    ],
    "Mid Cap": [
        {"name": "Axis Midcap",                    "scheme_code": 120505},
        {"name": "HDFC Midcap Opportunities",      "scheme_code": 100022},
        {"name": "Nippon India Growth",            "scheme_code": 118776},
        {"name": "Kotak Emerging Equity",          "scheme_code": 120238},
        {"name": "DSP Midcap",                     "scheme_code": 119786},
    ],
    "Small Cap": [
        {"name": "Axis Small Cap",                 "scheme_code": 125354},
        {"name": "Nippon India Small Cap",         "scheme_code": 118778},
        {"name": "Kotak Small Cap",                "scheme_code": 120230},
        {"name": "SBI Small Cap",                  "scheme_code": 125497},
        {"name": "HDFC Small Cap",                 "scheme_code": 100026},
    ],
    "Flexi Cap": [
        {"name": "Parag Parikh Flexi Cap",         "scheme_code": 122639},
        {"name": "HDFC Flexi Cap",                 "scheme_code": 100035},
        {"name": "UTI Flexi Cap",                  "scheme_code": 120848},
        {"name": "Canara Robeco Flexi Cap",        "scheme_code": 119019},
        {"name": "Mirae Asset Flexi Cap",          "scheme_code": 135781},
    ],
    "ELSS (Tax Saving)": [
        {"name": "Axis Long Term Equity",          "scheme_code": 119551},
        {"name": "Mirae Asset Tax Saver",          "scheme_code": 118825},
        {"name": "Canara Robeco ELSS",             "scheme_code": 119028},
        {"name": "Quant ELSS",                     "scheme_code": 120175},
        {"name": "DSP Tax Saver",                  "scheme_code": 119233},
    ],
    "Index Funds": [
        {"name": "UTI Nifty 50 Index",             "scheme_code": 120716},
        {"name": "HDFC Index Nifty 50",            "scheme_code": 120753},
        {"name": "ICICI Pru Nifty Index",          "scheme_code": 119100},
        {"name": "Nippon India Index Nifty 50",    "scheme_code": 120828},
        {"name": "UTI Nifty Next 50 Index",        "scheme_code": 120757},
    ],
    "Sectoral / Thematic": [
        {"name": "ICICI Pru Technology",           "scheme_code": 120584},
        {"name": "SBI Healthcare Opp",             "scheme_code": 125354},
        {"name": "Mirae Asset Healthcare",         "scheme_code": 148463},
        {"name": "Tata Digital India",             "scheme_code": 145552},
        {"name": "Nippon India Pharma",            "scheme_code": 118783},
    ],
    "Hybrid": [
        {"name": "ICICI Pru Balanced Advantage",   "scheme_code": 101206},
        {"name": "Mirae Asset Hybrid Equity",      "scheme_code": 118989},
        {"name": "DSP Aggressive Hybrid",          "scheme_code": 119234},
        {"name": "HDFC Balanced Advantage",        "scheme_code": 100035},
        {"name": "Canara Robeco Hybrid Aggressive","scheme_code": 119027},
    ],
    "Debt": [
        {"name": "Axis Liquid Fund",               "scheme_code": 120178},
        {"name": "HDFC Corporate Bond",            "scheme_code": 119270},
        {"name": "ICICI Pru Short Term",           "scheme_code": 120579},
        {"name": "Axis Short Duration",            "scheme_code": 120509},
        {"name": "SBI Magnum Gilt",                "scheme_code": 119591},
    ],
}

# Risk profile per category
RISK_PROFILE = {
    "Large Cap":            "Low-Medium",
    "Mid Cap":              "Medium-High",
    "Small Cap":            "High",
    "Flexi Cap":            "Medium-High",
    "ELSS (Tax Saving)":    "Medium-High",
    "Index Funds":          "Low-Medium",
    "Sectoral / Thematic":  "Very High",
    "Hybrid":               "Medium",
    "Debt":                 "Low",
}


def _get(url: str, timeout: int = 10) -> dict | list | None:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def search_funds(query: str) -> list[dict]:
    """Search mfapi.in by fund name. Returns [{schemeCode, schemeName}]."""
    data = _get(f"{MFAPI_BASE}/search?q={requests.utils.quote(query)}")
    return data if isinstance(data, list) else []


def fetch_fund_nav(scheme_code: int) -> pd.DataFrame | None:
    """
    Fetch full NAV history for a scheme.
    Returns DataFrame with columns [date, nav] sorted ascending, or None on failure.
    """
    data = _get(f"{MFAPI_BASE}/{scheme_code}")
    if not data or "data" not in data or not data["data"]:
        return None
    rows = data["data"]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna().sort_values("date").reset_index(drop=True)
    # Attach meta
    meta = data.get("meta", {})
    df.attrs["scheme_name"] = meta.get("scheme_name", "")
    df.attrs["fund_house"]   = meta.get("fund_house", "")
    df.attrs["scheme_type"]  = meta.get("scheme_type", "")
    return df


def _nav_on_or_before(df: pd.DataFrame, target_date: datetime) -> float | None:
    """Return the NAV value on or just before target_date."""
    subset = df[df["date"] <= target_date]
    if subset.empty:
        return None
    return float(subset.iloc[-1]["nav"])


def calculate_returns(df: pd.DataFrame) -> dict:
    """
    Compute point-to-point returns for standard periods.
    Returns dict with keys: 1M, 3M, 6M, 1Y, 3Y, 5Y (float % or None).
    Also includes: current_nav, std_dev_1y (annualised), sharpe_1y (approx).
    """
    if df is None or df.empty:
        return {}

    today = df["date"].max()
    current_nav = float(df.iloc[-1]["nav"])

    def ptp_return(months: int) -> float | None:
        past = today - pd.DateOffset(months=months)
        past_nav = _nav_on_or_before(df, past)
        if past_nav and past_nav > 0:
            r = (current_nav - past_nav) / past_nav * 100
            return round(r, 2)
        return None

    def cagr(years: int) -> float | None:
        past = today - pd.DateOffset(years=years)
        past_nav = _nav_on_or_before(df, past)
        if past_nav and past_nav > 0:
            r = ((current_nav / past_nav) ** (1 / years) - 1) * 100
            return round(r, 2)
        return None

    # Volatility: annualised std dev of daily returns (last 1 year)
    one_yr_ago = today - pd.DateOffset(years=1)
    recent = df[df["date"] >= one_yr_ago].copy()
    if len(recent) > 5:
        recent["daily_ret"] = recent["nav"].pct_change()
        std_dev = float(recent["daily_ret"].std() * np.sqrt(252) * 100)
        mean_ret = float(recent["daily_ret"].mean() * 252 * 100)
        sharpe = round((mean_ret - 6.5) / std_dev, 2) if std_dev > 0 else None  # risk-free ≈ 6.5%
    else:
        std_dev = None
        sharpe = None

    return {
        "current_nav": round(current_nav, 4),
        "1M":          ptp_return(1),
        "3M":          ptp_return(3),
        "6M":          ptp_return(6),
        "1Y":          ptp_return(12),
        "3Y":          cagr(3),
        "5Y":          cagr(5),
        "std_dev_1y":  round(std_dev, 2) if std_dev else None,
        "sharpe_1y":   sharpe,
    }


def score_fund(returns: dict, category: str = "") -> int:
    """
    Score a fund 0–100 based on returns + risk.
    Higher is better; penalises for high volatility in low-risk categories.
    """
    score = 0

    def add(val, thresholds: list[tuple[float, int]]) -> int:
        if val is None:
            return 0
        for cutoff, pts in sorted(thresholds, reverse=True):
            if val >= cutoff:
                return pts
        return 0

    # 1Y return (35 pts)
    score += add(returns.get("1Y"), [(30, 35), (20, 28), (15, 20), (10, 12), (5, 6), (0, 2)])
    # 3Y CAGR (30 pts)
    score += add(returns.get("3Y"), [(25, 30), (18, 24), (12, 18), (8, 10), (0, 4)])
    # 6M (15 pts)
    score += add(returns.get("6M"), [(15, 15), (10, 11), (5, 7), (0, 3)])
    # 3M (10 pts)
    score += add(returns.get("3M"), [(8, 10), (5, 7), (2, 4), (0, 1)])
    # Sharpe ratio (10 pts)
    score += add(returns.get("sharpe_1y"), [(2.0, 10), (1.5, 8), (1.0, 5), (0.5, 2)])

    return min(score, 100)


def get_recommendation(score: int, category: str, returns: dict) -> str:
    """Return a text recommendation label."""
    risk = RISK_PROFILE.get(category, "Medium")
    r1y = returns.get("1Y")
    r3y = returns.get("3Y")

    if score >= 70:
        return "Strong Buy"
    elif score >= 55:
        return "Buy"
    elif score >= 40:
        return "Hold"
    else:
        return "Avoid"


def build_funds_dataframe(category_filter: str | None = None) -> pd.DataFrame:
    """
    Fetch data for all curated funds (or a single category) and return a
    summary DataFrame ready for display.
    """
    records = []
    categories = (
        {category_filter: POPULAR_FUNDS[category_filter]}
        if category_filter and category_filter in POPULAR_FUNDS
        else POPULAR_FUNDS
    )

    for cat, funds in categories.items():
        for fund in funds:
            df = fetch_fund_nav(fund["scheme_code"])
            if df is None or df.empty:
                continue
            ret = calculate_returns(df)
            if not ret:
                continue
            s = score_fund(ret, cat)
            rec = get_recommendation(s, cat, ret)
            records.append({
                "Fund":         fund["name"],
                "Category":     cat,
                "Risk":         RISK_PROFILE.get(cat, "Medium"),
                "NAV (₹)":     ret["current_nav"],
                "1M %":        ret.get("1M"),
                "3M %":        ret.get("3M"),
                "6M %":        ret.get("6M"),
                "1Y %":        ret.get("1Y"),
                "3Y CAGR %":   ret.get("3Y"),
                "5Y CAGR %":   ret.get("5Y"),
                "Volatility":  ret.get("std_dev_1y"),
                "Sharpe (1Y)": ret.get("sharpe_1y"),
                "Score":       s,
                "Recommendation": rec,
                "scheme_code": fund["scheme_code"],
            })

    return pd.DataFrame(records)


def get_nav_history(scheme_code: int) -> pd.DataFrame | None:
    """Return full NAV history df for charting."""
    return fetch_fund_nav(scheme_code)
