import sys
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from deps import verify_supabase_jwt
from services.cache import cached
from services.limiter import limiter
from services.logger import get_logger
from services.market_hours import adaptive_ttl
from services.serializers import clean_dict

log = get_logger(__name__)
router = APIRouter()

_TICKER = Query(..., pattern=r"^[A-Z0-9.\-&]{1,30}$", description="Ticker e.g. RELIANCE.NS")


def _scope_readout(scope: str) -> dict:
    from tools.fetch_news import fetch_feed_items
    from tools.aggregate_sentiment import build_readout
    return build_readout(fetch_feed_items(scope, limit=60))


@router.get("/sentiment/market")
@limiter.limit("20/minute")
async def get_market_sentiment(
    request: Request,
    user: dict = Depends(verify_supabase_jwt),
):
    """India + world market news sentiment (independent readouts)."""
    async def _compute():
        import asyncio
        india, world = await asyncio.gather(
            asyncio.to_thread(_scope_readout, "india"),
            asyncio.to_thread(_scope_readout, "world"),
        )
        return {"india": india, "world": world}

    try:
        data = await cached("sentiment:market", ttl=adaptive_ttl(1800), fn=_compute)
    except Exception as e:
        log.exception("Market sentiment failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Market sentiment failed: {e}")

    return {
        "india": clean_dict(data["india"]),
        "world": clean_dict(data["world"]),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sentiment/stock")
@limiter.limit("20/minute")
async def get_stock_sentiment(
    request: Request,
    ticker: str = _TICKER,
    user: dict = Depends(verify_supabase_jwt),
):
    """Per-stock news sentiment + India/world reference labels."""
    cache_key = f"sentiment:stock:{ticker}"

    def _compute():
        from tools.fetch_news import fetch_stock_news
        from tools.aggregate_sentiment import build_readout
        # Strip the exchange suffix for a cleaner news query (RELIANCE.NS -> RELIANCE).
        query = ticker.split(".")[0]
        stock = build_readout(fetch_stock_news(query))
        india = _scope_readout("india")
        world = _scope_readout("world")
        return {
            "sentiment": stock,
            "market": {"india_label": india["label"], "world_label": world["label"]},
        }

    try:
        data = await cached(cache_key, ttl=adaptive_ttl(3600), fn=_compute)
    except Exception as e:
        log.exception("Stock sentiment failed for %s: %s", ticker, e)
        raise HTTPException(status_code=503, detail=f"Stock sentiment failed: {e}")

    return {
        "ticker": ticker,
        "sentiment": clean_dict(data["sentiment"]),
        "market": data["market"],
    }
