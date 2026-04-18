import sys
import os

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
        from tools.fetch_stock_data import fetch_ohlcv
        from tools.compute_indicators import compute_all
        from tools.ml_predictor import train_and_predict

        def _predict():
            df = fetch_ohlcv(ticker, "1d", period)
            df = compute_all(df)
            return train_and_predict(df)

        prediction = await cached(cache_key, ttl=3600, fn=_predict)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("ML prediction failed for %s: %s", ticker, e)
        raise HTTPException(status_code=503, detail=f"ML prediction failed: {e}")

    return {"ticker": ticker, **prediction}
