import sys
import os
import asyncio
import pandas as pd

from fastapi import APIRouter, Depends, HTTPException, Query, Request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from deps import verify_supabase_jwt
from services.cache import cached, cache_clear
from services.limiter import limiter
from services.logger import get_logger
from services.market_hours import adaptive_ttl
from services.serializers import clean_dict

log = get_logger(__name__)
router = APIRouter()

_TICKER = Query(..., pattern=r"^[A-Z0-9.\-&]{1,30}$", description="Ticker e.g. RELIANCE.NS")
_PERIOD  = Query("1y", pattern=r"^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$")


@router.get("/analysis/fundamentals")
async def get_fundamentals(
    ticker: str = _TICKER,
    user: dict = Depends(verify_supabase_jwt),
):
    """Fetch fundamental analysis data for a ticker (screener.in + yfinance)."""
    cache_key = f"fundamentals:{ticker}"

    try:
        from tools.fetch_fundamentals import fetch_fundamentals, score_fundamentals

        data = await cached(cache_key, ttl=adaptive_ttl(14400), fn=lambda: fetch_fundamentals(ticker))

        non_identity = {"name", "sector", "industry"}
        has_data = any(v is not None for k, v in data.items() if k not in non_identity)
        if not has_data:
            cache_clear(cache_key)
            data = await cached(cache_key, ttl=300, fn=lambda: fetch_fundamentals(ticker))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("Fundamentals fetch failed for %s: %s", ticker, e)
        raise HTTPException(status_code=503, detail=f"Fundamentals fetch failed: {e}")

    scoring = score_fundamentals(data)
    return {
        "ticker": ticker,
        "fundamentals": clean_dict(data),
        "score": scoring["score"],
        "grade": scoring["grade"],
        "breakdown": clean_dict(scoring["breakdown"]),
    }


@router.get("/analysis/ml-predict")
@limiter.limit("5/minute")
async def get_ml_prediction(
    request: Request,
    ticker: str = _TICKER,
    period: str = _PERIOD,
    user: dict = Depends(verify_supabase_jwt),
):
    """Run ML model to predict next-day price direction for a ticker."""
    cache_key = f"ml-predict:{ticker}:{period}"

    try:
        from services.daily_data import get_daily_df
        from tools.compute_indicators import compute_all
        from tools.ml_predictor import train_and_predict

        async def _predict():
            df = await get_daily_df(ticker, period)
            return await asyncio.to_thread(lambda: train_and_predict(compute_all(df.copy())))

        prediction = await cached(cache_key, ttl=3600, fn=_predict)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("ML prediction failed for %s: %s", ticker, e)
        raise HTTPException(status_code=503, detail=f"ML prediction failed: {e}")

    return {"ticker": ticker, **prediction}


@router.get("/analysis/confluence")
@limiter.limit("10/minute")
async def get_confluence(
    request: Request,
    ticker: str = _TICKER,
    user: dict = Depends(verify_supabase_jwt),
):
    """Run signal across 1D / 1W / 1M timeframes and return a confluence grid."""
    cache_key = f"confluence:{ticker}"

    async def _compute_all():
        from services.daily_data import get_daily_df, resample_ohlcv
        from tools.compute_indicators import compute_all
        from tools.generate_signals import generate_signal

        # One 5y daily fetch; 1W/1M candles are resampled from it instead of
        # three separate yfinance downloads.
        daily = await get_daily_df(ticker, "5y")

        def _signal_rows():
            two_years = daily[daily.index >= daily.index[-1] - pd.DateOffset(years=2)]
            frames = [
                ("1D", daily.tail(63).copy()),           # ~3 months of sessions
                ("1W", resample_ohlcv(two_years, "W-FRI")),
                ("1M", resample_ohlcv(daily, "ME")),
            ]
            rows = []
            for label, frame in frames:
                try:
                    sig = generate_signal(compute_all(frame))
                    rows.append({
                        "timeframe": label,
                        "signal": sig["signal"],
                        "confidence": sig["confidence"],
                        "components": {
                            k: {"points": v["points"], "label": v["signal"]}
                            for k, v in sig["components"].items()
                        },
                    })
                except Exception as e:
                    log.exception("Confluence %s %s failed: %s", ticker, label, e)
                    rows.append({"timeframe": label, "signal": None,
                                 "confidence": None, "components": {}})
            return rows

        return await asyncio.to_thread(_signal_rows)

    timeframes = await cached(cache_key, ttl=adaptive_ttl(600), fn=_compute_all)

    # Derive overall confluence summary
    signals = [t["signal"] for t in timeframes if t["signal"]]
    buy_count  = signals.count("BUY")
    sell_count = signals.count("SELL")
    hold_count = signals.count("HOLD")

    if buy_count == 3:
        strength = "Strong BUY"
    elif sell_count == 3:
        strength = "Strong SELL"
    elif buy_count >= 2:
        strength = "Moderate BUY"
    elif sell_count >= 2:
        strength = "Moderate SELL"
    elif hold_count >= 2:
        strength = "Neutral"
    else:
        strength = "Mixed"

    return {
        "ticker": ticker,
        "timeframes": timeframes,
        "summary": {
            "strength": strength,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
        },
    }


@router.get("/analysis/backtest")
async def get_backtest(
    ticker: str = _TICKER,
    period: str = _PERIOD,
    user: dict = Depends(verify_supabase_jwt),
):
    """Walk-forward backtest of the indicator signal strategy on daily OHLCV."""
    cache_key = f"backtest:{ticker}:{period}"

    try:
        from services.daily_data import get_daily_df
        from tools.compute_indicators import compute_all
        from tools.backtester import run_backtest

        async def _run():
            df = await get_daily_df(ticker, period)
            return await asyncio.to_thread(lambda: run_backtest(compute_all(df.copy())))

        result = await cached(cache_key, ttl=adaptive_ttl(21600), fn=_run)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("Backtest failed for %s: %s", ticker, e)
        raise HTTPException(status_code=503, detail=f"Backtest failed: {e}")

    return {"ticker": ticker, **result}
