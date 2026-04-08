"""
Fundamental analysis data fetcher.
Primary source: yfinance Ticker.info — let yfinance manage its own session (yfinance 1.x
uses curl_cffi internally and rejects external requests.Session objects).
Fallback: compute key metrics from income_stmt + balance_sheet when .info returns empty.
"""

import yfinance as yf
import pandas as pd


# ── Statement row reader ───────────────────────────────────────────────────────
def _row(df: pd.DataFrame, candidates: list):
    """
    Return the float value of the most-recent column from the first matching row.
    Tries each candidate name in order; returns None if none match.
    """
    if df is None or df.empty:
        return None
    for name in candidates:
        if name in df.index:
            try:
                series = df.loc[name].dropna()
                if len(series) > 0:
                    val = float(series.iloc[0])
                    return None if pd.isna(val) else val
            except (TypeError, ValueError):
                continue
    return None


# ── Main fetcher ───────────────────────────────────────────────────────────────
def fetch_fundamentals(ticker: str) -> dict:
    """
    Fetch fundamental metrics for a stock.
    Strategy:
      1. Try yf.Ticker.info — yfinance 1.x manages its own curl_cffi session.
      2. If .info returns fewer than 4 usable fields (cloud rate-limit), compute the
         key metrics from income_stmt + balance_sheet + fast_info.
    Returns a flat dict; all unavailable fields are None.
    """
    t = yf.Ticker(ticker)

    # ── Step 1: .info ──────────────────────────────────────────────────────────
    try:
        info = t.info or {}
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

    result = {
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

    # ── Step 2: statement fallback when .info was rate-limited ─────────────────
    useful = sum(1 for v in result.values() if v is not None)
    if useful < 4:
        result = _fill_from_statements(t, result)

    return result


def _fill_from_statements(t: yf.Ticker, result: dict) -> dict:
    """
    Fill missing fields by computing them from annual financial statements.
    This uses different Yahoo Finance endpoints that are less aggressively rate-limited.
    """
    try:
        income  = t.income_stmt    # rows = line items, cols = annual dates (newest first)
        balance = t.balance_sheet
    except Exception:
        income, balance = None, None

    # ── Profit margin: net_income / revenue ────────────────────────────────────
    if result.get("profit_margin") is None:
        rev = _row(income, ["Total Revenue", "Revenue"])
        ni  = _row(income, ["Net Income", "Net Income Common Stockholders",
                             "Net Income Including Noncontrolling Interests"])
        if rev and ni and rev != 0:
            result["profit_margin"] = ni / rev

    # ── Gross margin: gross_profit / revenue ───────────────────────────────────
    if result.get("gross_margin") is None:
        rev = _row(income, ["Total Revenue", "Revenue"])
        gp  = _row(income, ["Gross Profit"])
        if rev and gp and rev != 0:
            result["gross_margin"] = gp / rev

    # ── ROE: net_income / shareholders_equity ──────────────────────────────────
    if result.get("roe") is None:
        ni = _row(income, ["Net Income", "Net Income Common Stockholders",
                            "Net Income Including Noncontrolling Interests"])
        eq = _row(balance, ["Stockholders Equity", "Common Stock Equity",
                             "Total Equity Gross Minority Interest",
                             "Stockholders' Equity"])
        if ni and eq and eq != 0:
            result["roe"] = ni / eq

    # ── ROA: net_income / total_assets ─────────────────────────────────────────
    if result.get("roa") is None:
        ni = _row(income, ["Net Income", "Net Income Common Stockholders"])
        ta = _row(balance, ["Total Assets"])
        if ni and ta and ta != 0:
            result["roa"] = ni / ta

    # ── Debt / Equity (reported as % to match yfinance .info convention) ───────
    if result.get("debt_to_equity") is None:
        debt = _row(balance, ["Total Debt", "Long Term Debt",
                               "Long Term Debt And Capital Lease Obligation"])
        eq   = _row(balance, ["Stockholders Equity", "Common Stock Equity",
                               "Total Equity Gross Minority Interest"])
        if debt is not None and eq and eq != 0:
            result["debt_to_equity"] = (debt / eq) * 100  # match .info scale

    # ── Revenue growth: YoY comparison ─────────────────────────────────────────
    if result.get("revenue_growth") is None and income is not None and not income.empty:
        for name in ["Total Revenue", "Revenue"]:
            if name in income.index:
                try:
                    rev_series = income.loc[name].dropna()
                    if len(rev_series) >= 2:
                        r0 = float(rev_series.iloc[0])
                        r1 = float(rev_series.iloc[1])
                        if r1 != 0 and not pd.isna(r0) and not pd.isna(r1):
                            result["revenue_growth"] = (r0 - r1) / abs(r1)
                    break
                except (TypeError, ValueError):
                    continue

    # ── Earnings growth: YoY net income comparison ─────────────────────────────
    if result.get("earnings_growth") is None and income is not None and not income.empty:
        for name in ["Net Income", "Net Income Common Stockholders"]:
            if name in income.index:
                try:
                    ni_series = income.loc[name].dropna()
                    if len(ni_series) >= 2:
                        n0 = float(ni_series.iloc[0])
                        n1 = float(ni_series.iloc[1])
                        if n1 != 0 and not pd.isna(n0) and not pd.isna(n1):
                            result["earnings_growth"] = (n0 - n1) / abs(n1)
                    break
                except (TypeError, ValueError):
                    continue

    # ── Market cap from fast_info (very different endpoint, rarely blocked) ────
    if result.get("market_cap") is None:
        try:
            result["market_cap"] = t.fast_info.market_cap
        except Exception:
            pass

    return result


# ── Scoring ────────────────────────────────────────────────────────────────────
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
            pts, label = 15, "Excellent (PE < 15)"
        elif pe < 25:
            pts, label = 12, "Good (PE 15–25)"
        elif pe < 40:
            pts, label = 8,  "Fair (PE 25–40)"
        else:
            pts, label = 2,  "Expensive (PE > 40)"
    else:
        pts, label = 0, "N/A"
    breakdown["PE Ratio"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # ── Profitability: ROE (15 pts) ────────────────────────────────────────────
    roe = data.get("roe")
    if roe is not None:
        roe_pct = roe * 100
        if roe_pct > 20:
            pts, label = 15, f"Excellent ({roe_pct:.1f}%)"
        elif roe_pct > 15:
            pts, label = 12, f"Good ({roe_pct:.1f}%)"
        elif roe_pct > 10:
            pts, label = 8,  f"Fair ({roe_pct:.1f}%)"
        else:
            pts, label = 2,  f"Weak ({roe_pct:.1f}%)"
    else:
        pts, label = 0, "N/A"
    breakdown["ROE"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # ── Financial health: D/E ratio (15 pts) ──────────────────────────────────
    de = data.get("debt_to_equity")
    if de is not None:
        if de < 30:
            pts, label = 15, f"Low debt ({de:.1f})"
        elif de < 80:
            pts, label = 10, f"Moderate ({de:.1f})"
        elif de < 150:
            pts, label = 5,  f"High ({de:.1f})"
        else:
            pts, label = 0,  f"Very High ({de:.1f})"
    else:
        pts, label = 0, "N/A"
    breakdown["Debt / Equity"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # ── Growth: Revenue growth (15 pts) ───────────────────────────────────────
    rg = data.get("revenue_growth")
    if rg is not None:
        rg_pct = rg * 100
        if rg_pct > 20:
            pts, label = 15, f"Strong ({rg_pct:.1f}%)"
        elif rg_pct > 10:
            pts, label = 10, f"Good ({rg_pct:.1f}%)"
        elif rg_pct > 5:
            pts, label = 6,  f"Moderate ({rg_pct:.1f}%)"
        elif rg_pct > 0:
            pts, label = 3,  f"Slow ({rg_pct:.1f}%)"
        else:
            pts, label = 0,  f"Declining ({rg_pct:.1f}%)"
    else:
        pts, label = 0, "N/A"
    breakdown["Revenue Growth"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # ── Profitability: Net margin (15 pts) ────────────────────────────────────
    pm = data.get("profit_margin")
    if pm is not None:
        pm_pct = pm * 100
        if pm_pct > 20:
            pts, label = 15, f"Excellent ({pm_pct:.1f}%)"
        elif pm_pct > 12:
            pts, label = 10, f"Good ({pm_pct:.1f}%)"
        elif pm_pct > 5:
            pts, label = 6,  f"Fair ({pm_pct:.1f}%)"
        else:
            pts, label = 2,  f"Thin ({pm_pct:.1f}%)"
    else:
        pts, label = 0, "N/A"
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
