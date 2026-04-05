"""
Fundamental analysis data fetcher.
Uses yfinance Ticker.info — free, no API key required.
"""

import yfinance as yf


def fetch_fundamentals(ticker: str) -> dict:
    """
    Fetch fundamental metrics for a stock via yfinance.
    Returns a flat dict with None for unavailable fields.
    """
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        info = {}

    def _get(key, cast=float):
        val = info.get(key)
        if val is None:
            return None
        try:
            return cast(val)
        except (TypeError, ValueError):
            return None

    return {
        # Valuation
        "pe_trailing":     _get("trailingPE"),
        "pe_forward":      _get("forwardPE"),
        "pb_ratio":        _get("priceToBook"),
        "peg_ratio":       _get("pegRatio"),
        "ev_ebitda":       _get("enterpriseToEbitda"),
        # Profitability
        "roe":             _get("returnOnEquity"),
        "roa":             _get("returnOnAssets"),
        "profit_margin":   _get("profitMargins"),
        "gross_margin":    _get("grossMargins"),
        "op_margin":       _get("operatingMargins"),
        # Growth
        "revenue_growth":  _get("revenueGrowth"),
        "earnings_growth": _get("earningsGrowth"),
        # Financial health
        "debt_to_equity":  _get("debtToEquity"),
        "current_ratio":   _get("currentRatio"),
        "quick_ratio":     _get("quickRatio"),
        # Dividends
        "dividend_yield":  _get("dividendYield"),
        "payout_ratio":    _get("payoutRatio"),
        # Analyst
        "target_price":    _get("targetMeanPrice"),
        "recommendation":  _get("recommendationKey", cast=str),
        "analyst_count":   _get("numberOfAnalystOpinions", cast=int),
        # Market
        "market_cap":      _get("marketCap"),
        "beta":            _get("beta"),
        "week52_change":   _get("52WeekChange"),
        # Identity
        "name":            _get("shortName", cast=str),
        "sector":          _get("sector", cast=str),
        "industry":        _get("industry", cast=str),
    }


def score_fundamentals(data: dict, current_price: float = None) -> dict:
    """
    Score fundamental data on a 0–100 scale.
    Returns {"score": int, "grade": str, "breakdown": dict}.
    """
    breakdown = {}
    total = 0

    # ── Valuation: PE ratio (15 pts) ──────────────────────────────────────────
    pe = data.get("pe_trailing")
    if pe is not None and pe > 0:
        if pe < 15:
            pts = 15
            label = "Excellent (PE < 15)"
        elif pe < 25:
            pts = 12
            label = "Good (PE 15–25)"
        elif pe < 40:
            pts = 8
            label = "Fair (PE 25–40)"
        else:
            pts = 2
            label = "Expensive (PE > 40)"
    else:
        pts = 0
        label = "N/A"
    breakdown["PE Ratio"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # ── Profitability: ROE (15 pts) ────────────────────────────────────────────
    roe = data.get("roe")
    if roe is not None:
        roe_pct = roe * 100
        if roe_pct > 20:
            pts = 15
            label = f"Excellent ({roe_pct:.1f}%)"
        elif roe_pct > 15:
            pts = 12
            label = f"Good ({roe_pct:.1f}%)"
        elif roe_pct > 10:
            pts = 8
            label = f"Fair ({roe_pct:.1f}%)"
        else:
            pts = 2
            label = f"Weak ({roe_pct:.1f}%)"
    else:
        pts = 0
        label = "N/A"
    breakdown["ROE"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # ── Financial health: D/E ratio (15 pts) ──────────────────────────────────
    de = data.get("debt_to_equity")
    if de is not None:
        if de < 30:
            pts = 15
            label = f"Low debt ({de:.1f})"
        elif de < 80:
            pts = 10
            label = f"Moderate ({de:.1f})"
        elif de < 150:
            pts = 5
            label = f"High ({de:.1f})"
        else:
            pts = 0
            label = f"Very High ({de:.1f})"
    else:
        pts = 0
        label = "N/A"
    breakdown["Debt / Equity"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # ── Growth: Revenue growth (15 pts) ───────────────────────────────────────
    rg = data.get("revenue_growth")
    if rg is not None:
        rg_pct = rg * 100
        if rg_pct > 20:
            pts = 15
            label = f"Strong ({rg_pct:.1f}%)"
        elif rg_pct > 10:
            pts = 10
            label = f"Good ({rg_pct:.1f}%)"
        elif rg_pct > 5:
            pts = 6
            label = f"Moderate ({rg_pct:.1f}%)"
        elif rg_pct > 0:
            pts = 3
            label = f"Slow ({rg_pct:.1f}%)"
        else:
            pts = 0
            label = f"Declining ({rg_pct:.1f}%)"
    else:
        pts = 0
        label = "N/A"
    breakdown["Revenue Growth"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # ── Profitability: Net margin (15 pts) ────────────────────────────────────
    pm = data.get("profit_margin")
    if pm is not None:
        pm_pct = pm * 100
        if pm_pct > 20:
            pts = 15
            label = f"Excellent ({pm_pct:.1f}%)"
        elif pm_pct > 12:
            pts = 10
            label = f"Good ({pm_pct:.1f}%)"
        elif pm_pct > 5:
            pts = 6
            label = f"Fair ({pm_pct:.1f}%)"
        else:
            pts = 2
            label = f"Thin ({pm_pct:.1f}%)"
    else:
        pts = 0
        label = "N/A"
    breakdown["Profit Margin"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # ── Analyst view (25 pts) ─────────────────────────────────────────────────
    analyst_pts = 0
    analyst_label_parts = []

    rec = (data.get("recommendation") or "").lower()
    if rec in ("strong_buy", "strongbuy", "buy"):
        analyst_pts += 15
        analyst_label_parts.append("Analyst: BUY")
    elif rec in ("hold", "neutral"):
        analyst_pts += 8
        analyst_label_parts.append("Analyst: HOLD")
    elif rec in ("sell", "underperform", "strong_sell"):
        analyst_pts += 0
        analyst_label_parts.append("Analyst: SELL")

    target = data.get("target_price")
    if target and current_price and current_price > 0:
        upside = ((target - current_price) / current_price) * 100
        if upside > 15:
            analyst_pts += 10
            analyst_label_parts.append(f"Upside {upside:.1f}%")
        elif upside > 0:
            analyst_pts += 5
            analyst_label_parts.append(f"Upside {upside:.1f}%")
        else:
            analyst_label_parts.append(f"Downside {upside:.1f}%")

    breakdown["Analyst View"] = {
        "points": analyst_pts,
        "max": 25,
        "label": " · ".join(analyst_label_parts) if analyst_label_parts else "N/A",
    }
    total += analyst_pts

    # ── Grade ─────────────────────────────────────────────────────────────────
    if total >= 65:
        grade = "Strong"
    elif total >= 45:
        grade = "Fair"
    else:
        grade = "Weak"

    return {"score": total, "grade": grade, "breakdown": breakdown}
