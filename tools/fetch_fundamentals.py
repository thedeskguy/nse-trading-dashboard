"""
Fundamental analysis data fetcher.
Primary source:  screener.in (India-specific, no API key, consolidated financials).
                 Parses top-ratios panel + P&L table + Balance Sheet table.
Secondary:       yfinance — only for analyst targets, beta, sector/industry, forward PE.
All fields are always present in the returned dict; missing values are None.
"""

import re
import pandas as pd
import yfinance as yf


# ── helpers ────────────────────────────────────────────────────────────────────
def _strip(s: str) -> str:
    """Remove HTML tags and normalise whitespace / entities."""
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("\xa0", " ")
    return s.strip()


def _clean_label(s: str) -> str:
    """Normalise a table row label: strip HTML, trailing '+', extra spaces."""
    s = _strip(s)
    s = re.sub(r"\s*\+\s*$", "", s).strip()
    return s


def _num(s: str) -> float | None:
    """Parse Indian-format number strings (commas, %, Cr, ₹).  Returns None on failure."""
    s = re.sub(r"[,₹\s%]", "", _strip(s))
    s = re.sub(r"(Cr\.?|Lakh)$", "", s, flags=re.IGNORECASE)
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _table_rows(html: str, section_id: str) -> dict[str, list[float | None]]:
    """
    Parse an HTML table inside a section with the given id.
    Returns {row_label: [newest_val, prev_val, ...]} — newest first.
    Screener tables have years left→right (oldest→newest), so we reverse.
    Works with or without explicit <tbody> tags (browsers inject them;
    raw server HTML sometimes omits them).
    """
    idx = html.find(f'id="{section_id}"')
    if idx < 0:
        return {}
    # Take a generous chunk; stop at the next top-level section
    chunk = html[idx: idx + 40000]

    rows: dict[str, list[float | None]] = {}

    # Try to find rows inside <tbody> first, fall back to any <tr> inside chunk
    tbody_m = re.search(r"<tbody>([\s\S]*?)</tbody>", chunk)
    search_in = tbody_m.group(1) if tbody_m else chunk

    for tr in re.finditer(r"<tr[^>]*>([\s\S]*?)</tr>", search_in):
        cells = re.findall(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", tr.group(1))
        if len(cells) < 2:
            continue
        label = _clean_label(cells[0])
        if not label or label.startswith("Mar") or label.startswith("Sep"):
            continue   # skip header rows
        values = [_num(c) for c in cells[1:]]
        # Only keep rows that have at least one numeric value
        if any(v is not None for v in values):
            rows[label] = list(reversed(values))   # newest first

    return rows


# ── main screener scraper ──────────────────────────────────────────────────────
def _fetch_screener(ticker: str) -> dict:
    """
    Scrape screener.in/company/{SYMBOL}/consolidated/ for key fundamentals.

    Returned dict keys (all present, None if unavailable):
      pe_trailing, pb_ratio, book_value, roe, roce, dividend_yield,
      market_cap, face_value, high_52w, low_52w,
      revenue, revenue_growth, op_profit, opm_pct,
      net_profit, net_profit_margin, profit_growth,
      debt, equity, debt_to_equity, interest_coverage
    """
    # curl_cffi impersonates Chrome's TLS fingerprint — bypasses Cloudflare on cloud IPs
    try:
        from curl_cffi import requests as _req
        _impersonate = "chrome"
    except ImportError:
        import requests as _req
        _impersonate = None

    symbol = ticker.replace(".NS", "").replace(".BO", "").upper()

    result: dict[str, float | None] = {
        k: None for k in [
            "pe_trailing", "pb_ratio", "book_value", "roe", "roce",
            "dividend_yield", "market_cap", "face_value", "high_52w", "low_52w",
            "revenue", "revenue_growth", "op_profit", "opm_pct",
            "net_profit", "net_profit_margin", "profit_growth",
            "debt", "equity", "debt_to_equity", "interest_coverage",
        ]
    }

    def _get(url: str) -> str | None:
        try:
            kwargs = {"timeout": 20}
            if _impersonate:
                kwargs["impersonate"] = _impersonate
            else:
                kwargs["headers"] = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/123.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                }
            r = _req.get(url, **kwargs)
            return r.text if r.status_code == 200 else None
        except Exception:
            return None

    # Try consolidated first, fall back to standalone
    html = _get(f"https://www.screener.in/company/{symbol}/consolidated/")
    if not html or "Page not found" in html:
        html = _get(f"https://www.screener.in/company/{symbol}/")
    if not html:
        return result

    # ── Top-ratios panel ──────────────────────────────────────────────────────
    top_m = re.search(r'id="top-ratios">([\s\S]*?)</ul>', html)
    if top_m:
        # Collect ALL .number values per li (High/Low has two)
        for li in re.finditer(r'<li[^>]*>([\s\S]*?)</li>', top_m.group(1)):
            name_m = re.search(r'class="name"[^>]*>([\s\S]*?)</span>', li.group(1))
            if not name_m:
                continue
            name = _strip(name_m.group(1))
            all_nums = [_num(s) for s in re.findall(
                r'class="number"[^>]*>([\s\S]*?)</span>', li.group(1)
            )]
            all_nums = [n for n in all_nums if n is not None]
            if not all_nums:
                continue
            val = all_nums[0]

            if name == "Stock P/E":
                result["pe_trailing"] = val
            elif name == "Book Value":
                result["book_value"] = val
            elif name == "ROE":
                # screener shows as % string (e.g. "8.40" = 8.40%)
                result["roe"] = val / 100.0
            elif name == "ROCE":
                result["roce"] = val / 100.0
            elif name == "Dividend Yield":
                # screener shows "0.41" meaning 0.41% → store as fraction 0.0041
                # guard: if val > 10 it's already in %, e.g. "41" → /100/100 not needed
                result["dividend_yield"] = val / 100.0
            elif name == "Market Cap":
                # screener in Cr; "18,27,154" → 1827154 Cr → * 1e7 = ₹
                result["market_cap"] = val * 1e7
            elif name == "Face Value":
                result["face_value"] = val
            elif name == "High / Low":
                # Two .number spans: high and low
                if len(all_nums) >= 2:
                    result["high_52w"] = max(all_nums)
                    result["low_52w"]  = min(all_nums)

    # Compute Price/Book if we have both book value and market cap
    # (we need current price; skip here — caller can compute)

    # ── P&L table ─────────────────────────────────────────────────────────────
    pl = _table_rows(html, "profit-loss")

    def _latest2(key_candidates: list[str]) -> tuple[float | None, float | None]:
        """Return (latest, prev-year) from P&L rows, newest first."""
        for key in key_candidates:
            row = pl.get(key)
            if row:
                vals = [v for v in row if v is not None]
                if len(vals) >= 2:
                    return vals[0], vals[1]
                if len(vals) == 1:
                    return vals[0], None
        return None, None

    rev_latest, rev_prev = _latest2(["Sales", "Revenue"])
    result["revenue"] = rev_latest  # in Cr

    if rev_latest is not None and rev_prev is not None and rev_prev != 0:
        result["revenue_growth"] = (rev_latest - rev_prev) / abs(rev_prev)

    op_latest, _ = _latest2(["Operating Profit"])
    result["op_profit"] = op_latest

    if op_latest is not None and rev_latest and rev_latest != 0:
        result["opm_pct"] = op_latest / rev_latest  # fraction

    # OPM% from screener (pre-computed, as percentage string like "17")
    opm_row = pl.get("OPM %")
    if opm_row:
        opm_vals = [v for v in opm_row if v is not None]
        if opm_vals:
            result["opm_pct"] = opm_vals[0] / 100.0  # convert % → fraction

    net_latest, net_prev = _latest2(["Net Profit", "Profit after tax", "PAT"])
    result["net_profit"] = net_latest

    if net_latest is not None and rev_latest and rev_latest != 0:
        result["net_profit_margin"] = net_latest / rev_latest

    if net_latest is not None and net_prev is not None and net_prev != 0:
        result["profit_growth"] = (net_latest - net_prev) / abs(net_prev)

    # Interest coverage = Operating Profit / Interest
    interest_latest, _ = _latest2(["Interest"])
    if op_latest is not None and interest_latest and interest_latest != 0:
        result["interest_coverage"] = op_latest / interest_latest

    # ── Balance Sheet ──────────────────────────────────────────────────────────
    bs = _table_rows(html, "balance-sheet")

    def _bs_latest(key_candidates: list[str]) -> float | None:
        for key in key_candidates:
            row = bs.get(key)
            if row:
                vals = [v for v in row if v is not None]
                if vals:
                    return vals[0]
        return None

    equity_cap = _bs_latest(["Equity Capital"])
    reserves    = _bs_latest(["Reserves"])
    borrowings  = _bs_latest(["Borrowings"])

    if equity_cap is not None and reserves is not None:
        total_equity = equity_cap + reserves
        result["equity"] = total_equity
        if borrowings is not None:
            result["debt"] = borrowings
            if total_equity != 0:
                # Match yfinance convention: D/E expressed as %
                result["debt_to_equity"] = (borrowings / total_equity) * 100

    # Price/Book: book_value is ₹/share; need current price from market cap + shares
    # We leave pb_ratio to be computed by yfinance (it has EPS/price data)

    return result


# ── yfinance supplement (analyst & identity only) ─────────────────────────────
def _fetch_yfinance(ticker: str) -> dict:
    """
    Fetch only the fields that screener.in does not provide:
      forward_pe, peg_ratio, ev_ebitda, roa, current_ratio, quick_ratio,
      pb_ratio, beta, target_price, recommendation, analyst_count,
      week52_change, sector, industry, name.
    """
    result: dict = {k: None for k in [
        "pe_forward", "peg_ratio", "ev_ebitda", "roa",
        "current_ratio", "quick_ratio", "pb_ratio",
        "beta", "target_price", "recommendation", "analyst_count",
        "week52_change", "sector", "industry", "name",
    ]}
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return result

    def _get(key, cast=float):
        val = info.get(key)
        if val is None:
            return None
        try:
            return cast(val)
        except (TypeError, ValueError):
            return None

    result["pe_forward"]    = _get("forwardPE")
    result["peg_ratio"]     = _get("pegRatio")
    result["ev_ebitda"]     = _get("enterpriseToEbitda")
    result["roa"]           = _get("returnOnAssets")
    result["current_ratio"] = _get("currentRatio")
    result["quick_ratio"]   = _get("quickRatio")
    result["pb_ratio"]      = _get("priceToBook")
    result["beta"]          = _get("beta")
    result["target_price"]  = _get("targetMeanPrice")
    result["recommendation"]= _get("recommendationKey", cast=str)
    result["analyst_count"] = _get("numberOfAnalystOpinions", cast=int)
    result["week52_change"] = _get("52WeekChange")
    result["sector"]        = _get("sector", cast=str)
    result["industry"]      = _get("industry", cast=str)
    result["name"]          = _get("shortName", cast=str)
    return result


# ── public API ─────────────────────────────────────────────────────────────────
def fetch_fundamentals(ticker: str) -> dict:
    """
    Merge screener.in (primary) + yfinance (analyst / identity supplement).
    Returns a flat dict; unavailable fields are None.
    """
    screener = _fetch_screener(ticker)
    yf_data  = _fetch_yfinance(ticker)

    return {
        # ── Valuation ──────────────────────────────────────────────────────
        "pe_trailing":    screener.get("pe_trailing"),
        "pe_forward":     yf_data.get("pe_forward"),
        "pb_ratio":       yf_data.get("pb_ratio"),
        "book_value":     screener.get("book_value"),     # ₹/share
        "peg_ratio":      yf_data.get("peg_ratio"),
        "ev_ebitda":      yf_data.get("ev_ebitda"),
        "face_value":     screener.get("face_value"),
        # ── Profitability ──────────────────────────────────────────────────
        "roe":            screener.get("roe"),
        "roce":           screener.get("roce"),
        "roa":            yf_data.get("roa"),
        "op_margin":      screener.get("opm_pct"),
        "profit_margin":  screener.get("net_profit_margin"),
        # ── Income ────────────────────────────────────────────────────────
        "revenue":        screener.get("revenue"),         # Cr
        "op_profit":      screener.get("op_profit"),       # Cr
        "net_profit":     screener.get("net_profit"),      # Cr
        # ── Growth ────────────────────────────────────────────────────────
        "revenue_growth":  screener.get("revenue_growth"),
        "profit_growth":   screener.get("profit_growth"),
        # ── Financial health ───────────────────────────────────────────────
        "debt":            screener.get("debt"),            # Cr
        "equity":          screener.get("equity"),          # Cr
        "debt_to_equity":  screener.get("debt_to_equity"),
        "interest_coverage": screener.get("interest_coverage"),
        "current_ratio":   yf_data.get("current_ratio"),
        "quick_ratio":     yf_data.get("quick_ratio"),
        # ── Dividends ──────────────────────────────────────────────────────
        "dividend_yield":  screener.get("dividend_yield"),
        # ── Market ─────────────────────────────────────────────────────────
        "market_cap":      screener.get("market_cap"),
        "high_52w":        screener.get("high_52w"),
        "low_52w":         screener.get("low_52w"),
        "beta":            yf_data.get("beta"),
        "week52_change":   yf_data.get("week52_change"),
        # ── Analyst ────────────────────────────────────────────────────────
        "target_price":    yf_data.get("target_price"),
        "recommendation":  yf_data.get("recommendation"),
        "analyst_count":   yf_data.get("analyst_count"),
        # ── Identity ───────────────────────────────────────────────────────
        "name":            yf_data.get("name"),
        "sector":          yf_data.get("sector"),
        "industry":        yf_data.get("industry"),
    }


# ── Scoring ────────────────────────────────────────────────────────────────────
def score_fundamentals(data: dict, current_price: float = None) -> dict:
    """Score fundamental data 0–100. Returns {score, grade, breakdown}."""
    breakdown = {}
    total = 0

    # PE Ratio (15 pts)
    pe = data.get("pe_trailing")
    if pe is not None and pe > 0:
        if pe < 15:   pts, label = 15, f"Excellent (PE {pe:.1f}x)"
        elif pe < 25: pts, label = 12, f"Good (PE {pe:.1f}x)"
        elif pe < 40: pts, label = 8,  f"Fair (PE {pe:.1f}x)"
        else:          pts, label = 2,  f"Expensive (PE {pe:.1f}x)"
    else:
        pts, label = 0, "N/A"
    breakdown["PE Ratio"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # ROE (15 pts)
    roe = data.get("roe")
    if roe is not None:
        rp = roe * 100
        if rp > 20:   pts, label = 15, f"Excellent ({rp:.1f}%)"
        elif rp > 15: pts, label = 12, f"Good ({rp:.1f}%)"
        elif rp > 10: pts, label = 8,  f"Fair ({rp:.1f}%)"
        else:          pts, label = 2,  f"Weak ({rp:.1f}%)"
    else:
        pts, label = 0, "N/A"
    breakdown["ROE"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # Debt / Equity (15 pts)
    de = data.get("debt_to_equity")
    if de is not None:
        if de < 30:    pts, label = 15, f"Low debt (D/E {de:.1f})"
        elif de < 80:  pts, label = 10, f"Moderate (D/E {de:.1f})"
        elif de < 150: pts, label = 5,  f"High (D/E {de:.1f})"
        else:           pts, label = 0,  f"Very High (D/E {de:.1f})"
    else:
        pts, label = 0, "N/A"
    breakdown["Debt / Equity"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # Revenue Growth (15 pts)
    rg = data.get("revenue_growth")
    if rg is not None:
        rp = rg * 100
        if rp > 20:   pts, label = 15, f"Strong ({rp:.1f}%)"
        elif rp > 10: pts, label = 10, f"Good ({rp:.1f}%)"
        elif rp > 5:  pts, label = 6,  f"Moderate ({rp:.1f}%)"
        elif rp > 0:  pts, label = 3,  f"Slow ({rp:.1f}%)"
        else:          pts, label = 0,  f"Declining ({rp:.1f}%)"
    else:
        pts, label = 0, "N/A"
    breakdown["Revenue Growth"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # Net Profit Margin (15 pts)
    pm = data.get("profit_margin")
    if pm is not None:
        pp = pm * 100
        if pp > 20:   pts, label = 15, f"Excellent ({pp:.1f}%)"
        elif pp > 12: pts, label = 10, f"Good ({pp:.1f}%)"
        elif pp > 5:  pts, label = 6,  f"Fair ({pp:.1f}%)"
        else:          pts, label = 2,  f"Thin ({pp:.1f}%)"
    else:
        pts, label = 0, "N/A"
    breakdown["Net Margin"] = {"points": pts, "max": 15, "label": label}
    total += pts

    # Analyst View (25 pts)
    ap = 0
    alp = []
    rec = (data.get("recommendation") or "").lower()
    if rec in ("strong_buy", "strongbuy", "buy"):
        ap += 15; alp.append("Analyst: BUY")
    elif rec in ("hold", "neutral"):
        ap += 8;  alp.append("Analyst: HOLD")
    elif rec in ("sell", "underperform", "strong_sell"):
        alp.append("Analyst: SELL")

    target = data.get("target_price")
    if target and current_price and current_price > 0:
        upside = (target - current_price) / current_price * 100
        if upside > 15:  ap += 10; alp.append(f"Upside {upside:.1f}%")
        elif upside > 0: ap += 5;  alp.append(f"Upside {upside:.1f}%")
        else:             alp.append(f"Downside {upside:.1f}%")

    breakdown["Analyst View"] = {
        "points": ap, "max": 25,
        "label": " · ".join(alp) if alp else "N/A",
    }
    total += ap

    grade = "Strong" if total >= 65 else ("Fair" if total >= 45 else "Weak")
    return {"score": total, "grade": grade, "breakdown": breakdown}
