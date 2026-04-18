import sys
import os
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from deps import verify_supabase_jwt
from services.cache import cached
from services.serializers import df_to_records

router = APIRouter()

# Current Nifty 50 constituents — synced with NSE India on 2026-04-18
NIFTY_50 = [
    ("ADANIENT.NS",   "Adani Enterprises"),
    ("ADANIPORTS.NS", "Adani Ports"),
    ("APOLLOHOSP.NS", "Apollo Hospitals"),
    ("ASIANPAINT.NS", "Asian Paints"),
    ("AXISBANK.NS",   "Axis Bank"),
    ("BAJAJ-AUTO.NS", "Bajaj Auto"),
    ("BAJAJFINSV.NS", "Bajaj Finserv"),
    ("BAJFINANCE.NS", "Bajaj Finance"),
    ("BEL.NS",        "Bharat Electronics"),
    ("BHARTIARTL.NS", "Bharti Airtel"),
    ("CIPLA.NS",      "Cipla"),
    ("COALINDIA.NS",  "Coal India"),
    ("DRREDDY.NS",    "Dr. Reddy's"),
    ("EICHERMOT.NS",  "Eicher Motors"),
    ("ETERNAL.NS",    "Eternal (Zomato)"),
    ("GRASIM.NS",     "Grasim Industries"),
    ("HCLTECH.NS",    "HCL Technologies"),
    ("HDFCBANK.NS",   "HDFC Bank"),
    ("HDFCLIFE.NS",   "HDFC Life Insurance"),
    ("HINDALCO.NS",   "Hindalco Industries"),
    ("HINDUNILVR.NS", "Hindustan Unilever"),
    ("ICICIBANK.NS",  "ICICI Bank"),
    ("INDIGO.NS",     "InterGlobe Aviation (IndiGo)"),
    ("INFY.NS",       "Infosys"),
    ("ITC.NS",        "ITC"),
    ("JIOFIN.NS",     "Jio Financial Services"),
    ("JSWSTEEL.NS",   "JSW Steel"),
    ("KOTAKBANK.NS",  "Kotak Mahindra Bank"),
    ("LT.NS",         "Larsen & Toubro"),
    ("M&M.NS",        "Mahindra & Mahindra"),
    ("MARUTI.NS",     "Maruti Suzuki"),
    ("MAXHEALTH.NS",  "Max Healthcare"),
    ("NESTLEIND.NS",  "Nestle India"),
    ("NTPC.NS",       "NTPC"),
    ("ONGC.NS",       "ONGC"),
    ("POWERGRID.NS",  "Power Grid Corporation"),
    ("RELIANCE.NS",   "Reliance Industries"),
    ("SBILIFE.NS",    "SBI Life Insurance"),
    ("SBIN.NS",       "State Bank of India"),
    ("SHRIRAMFIN.NS", "Shriram Finance"),
    ("SUNPHARMA.NS",  "Sun Pharmaceutical"),
    ("TATACONSUM.NS", "Tata Consumer Products"),
    ("TATASTEEL.NS",  "Tata Steel"),
    ("TCS.NS",        "Tata Consultancy Services"),
    ("TECHM.NS",      "Tech Mahindra"),
    ("TITAN.NS",      "Titan Company"),
    ("TMPV.NS",       "Tata Motors"),
    ("TRENT.NS",      "Trent"),
    ("ULTRACEMCO.NS", "UltraTech Cement"),
    ("WIPRO.NS",      "Wipro"),
]

_INDICES = [
    {"key": "NIFTY50",   "ticker": "^NSEI",   "name": "NIFTY 50"},
    {"key": "BANKNIFTY", "ticker": "^NSEBANK", "name": "BANKNIFTY"},
    {"key": "SENSEX",    "ticker": "^BSESN",   "name": "SENSEX"},
]


@router.get("/market/indices")
async def get_indices(user: dict = Depends(verify_supabase_jwt)):
    """Return last price and day change % for major NSE/BSE indices."""
    from tools.fetch_stock_data import _fetch_yfinance

    result = []
    for idx in _INDICES:
        try:
            df = await asyncio.to_thread(_fetch_yfinance, idx["ticker"], "1d", "5d")
            if len(df) < 2:
                raise ValueError("not enough rows")
            prev_close = float(df["Close"].iloc[-2])
            last_price = float(df["Close"].iloc[-1])
            change_pct = ((last_price - prev_close) / prev_close) * 100
            result.append({
                "key": idx["key"],
                "name": idx["name"],
                "value": last_price,
                "change_pct": round(change_pct, 2),
                "up": change_pct >= 0,
            })
        except Exception:
            result.append({
                "key": idx["key"],
                "name": idx["name"],
                "value": None,
                "change_pct": None,
                "up": None,
            })
    return {"indices": result}


@router.get("/market/ohlcv")
async def get_ohlcv(
    ticker: str = Query(..., description="Ticker symbol e.g. RELIANCE.NS"),
    interval: str = Query("1d", description="Candle interval e.g. 1d, 1h, 15m"),
    period: str = Query("3mo", description="Lookback period e.g. 3mo, 1y"),
    with_indicators: bool = Query(False, description="Include EMA/Bollinger overlay series"),
    user: dict = Depends(verify_supabase_jwt),
):
    """Fetch OHLCV candlestick data for a ticker."""
    cache_key = f"ohlcv:{ticker}:{interval}:{period}:ind={int(with_indicators)}"

    try:
        from tools.fetch_stock_data import fetch_ohlcv

        def _fetch():
            df = fetch_ohlcv(ticker, interval, period)
            if with_indicators:
                from tools.compute_indicators import (
                    compute_emas, compute_bollinger, compute_rsi,
                    compute_macd, compute_obv,
                )
                df = compute_emas(df, [9, 21, 50, 200])
                df = compute_bollinger(df, period=20, std=2.0)
                df = compute_rsi(df, period=14)
                df = compute_macd(df)
                df = compute_obv(df)
            return df

        df = await cached(cache_key, ttl=300, fn=_fetch)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Market data API failure: {e}")

    if with_indicators:
        keep = [
            "Open", "High", "Low", "Close", "Volume",
            "EMA_9", "EMA_21", "EMA_50", "EMA_200",
            "BB_upper", "BB_middle", "BB_lower",
            "RSI_14", "MACD", "MACD_signal", "MACD_hist", "OBV",
        ]
        cols = [c for c in keep if c in df.columns]
        candles = df_to_records(df[cols].rename(columns=str.lower))
    else:
        candles = df_to_records(df.rename(columns=str.lower))
    return {
        "ticker": ticker,
        "interval": interval,
        "period": period,
        "candles": candles,
        "count": len(candles),
    }


@router.get("/market/search")
async def search_stocks(
    q: str = Query(..., min_length=1, description="Search query"),
    user: dict = Depends(verify_supabase_jwt),
):
    """Search NSE-listed stocks by name or ticker. Returns up to 10 matches."""
    import pandas as pd
    import httpx

    cache_key = "nse:equity_list"

    async def _fetch():
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    try:
        csv_text = await cached(cache_key, ttl=86400, fn=_fetch)
        from io import StringIO
        df = pd.read_csv(StringIO(csv_text))
        # Columns: SYMBOL, NAME OF COMPANY, ...
        df.columns = [c.strip() for c in df.columns]
        symbol_col = "SYMBOL"
        name_col = "NAME OF COMPANY"
        q_lower = q.lower()
        mask = (
            df[symbol_col].str.lower().str.contains(q_lower, na=False)
            | df[name_col].str.lower().str.contains(q_lower, na=False)
        )
        matches = df[mask][[symbol_col, name_col]].head(10)
        return {
            "results": [
                {"ticker": f"{row[symbol_col]}.NS", "name": row[name_col].title()}
                for _, row in matches.iterrows()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Stock search unavailable: {e}")


@router.get("/market/company-info")
async def get_company_info(
    ticker: str = Query(..., description="Ticker e.g. RELIANCE.NS"),
    user: dict = Depends(verify_supabase_jwt),
):
    """Return company display name for a ticker.

    Uses the NSE equity list CSV (already cached by /market/search) — fast,
    reliable, and works offline from yfinance.
    """
    import pandas as pd
    import httpx
    from io import StringIO

    cache_key = "nse:equity_list"

    async def _fetch():
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    try:
        csv_text = await cached(cache_key, ttl=86400, fn=_fetch)
        df = pd.read_csv(StringIO(csv_text))
        df.columns = [c.strip() for c in df.columns]
        symbol = ticker.upper().split(".")[0]  # RELIANCE.NS → RELIANCE
        row = df[df["SYMBOL"].str.upper() == symbol]
        if not row.empty:
            return {"ticker": ticker, "name": str(row.iloc[0]["NAME OF COMPANY"]).title()}
    except Exception:
        pass
    return {"ticker": ticker, "name": ticker}


@router.get("/market/signal")
async def get_signal(
    ticker: str = Query(..., description="Ticker symbol e.g. RELIANCE.NS"),
    interval: str = Query("1d", description="Candle interval"),
    period: str = Query("3mo", description="Lookback period"),
    user: dict = Depends(verify_supabase_jwt),
):
    """Compute buy/sell/hold signal for a ticker using technical indicators."""
    cache_key = f"signal:{ticker}:{interval}:{period}"

    try:
        from tools.fetch_stock_data import fetch_ohlcv
        from tools.compute_indicators import compute_all
        from tools.generate_signals import generate_signal

        def _compute():
            df = fetch_ohlcv(ticker, interval, period)
            df = compute_all(df)
            return generate_signal(df)

        signal = await cached(cache_key, ttl=300, fn=_compute)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Signal computation failed: {e}")


@router.get("/market/scan")
async def scan_nifty50(user: dict = Depends(verify_supabase_jwt)):
    """Batch technical signal scan for all Nifty 50 stocks. Cached 10 min."""
    cache_key = "scan:nifty50"

    async def _do_scan():
        from tools.fetch_stock_data import fetch_ohlcv
        from tools.compute_indicators import compute_all
        from tools.generate_signals import generate_signal

        sem = asyncio.Semaphore(8)

        async def _scan_one(ticker: str, name: str):
            async with sem:
                try:
                    def _compute():
                        df = fetch_ohlcv(ticker, "1d", "3mo")
                        change_pct = None
                        if len(df) >= 2:
                            prev = float(df["Close"].iloc[-2])
                            last = float(df["Close"].iloc[-1])
                            change_pct = round((last - prev) / prev * 100, 2)
                        df = compute_all(df)
                        sig = generate_signal(df)
                        return {
                            "ticker": ticker,
                            "name": name,
                            "signal": sig["signal"],
                            "confidence": sig["confidence"],
                            "last_price": sig["last_price"],
                            "change_pct": change_pct,
                        }
                    return await asyncio.to_thread(_compute)
                except Exception:
                    return {
                        "ticker": ticker, "name": name,
                        "signal": None, "confidence": None,
                        "last_price": None, "change_pct": None,
                    }

        tasks = [_scan_one(t, n) for t, n in NIFTY_50]
        return await asyncio.gather(*tasks)

    results = await cached(cache_key, ttl=600, fn=_do_scan)
    return {"stocks": list(results), "count": len(results)}

    return {"ticker": ticker, **signal}
