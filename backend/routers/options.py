import sys
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from deps import verify_supabase_jwt
from services.cache import cached
from services.limiter import limiter
from services.logger import get_logger
from services.serializers import df_to_records, clean_dict

log = get_logger(__name__)
router = APIRouter()

_SYMBOL = Query(..., pattern=r"^(NIFTY|BANKNIFTY|MIDCPNIFTY)$",
                description="Index symbol: NIFTY, BANKNIFTY, or MIDCPNIFTY")
_STYLE  = Query("both", pattern=r"^(intraday|positional|both)$",
                description="Trade style: intraday, positional, or both")


@router.get("/options/chain")
@limiter.limit("20/minute")
async def get_options_chain(
    request: Request,
    symbol: str = _SYMBOL,
    expiry: Optional[str] = Query(None, description="Expiry date string (optional, defaults to nearest)"),
    user: dict = Depends(verify_supabase_jwt),
):
    """Fetch live options chain for a given index symbol."""
    cache_key = f"options-chain:{symbol}:{expiry or 'nearest'}"

    try:
        from tools.fetch_options_chain import fetch_options_chain
        import pandas as pd

        result = await cached(cache_key, ttl=60, fn=lambda: fetch_options_chain(symbol, expiry))
    except Exception as e:
        log.exception("Options chain fetch failed for %s: %s", symbol, e)
        raise HTTPException(status_code=503, detail=f"Market data temporarily unavailable: {e}")

    output = {k: v for k, v in result.items() if k != "chain"}
    chain_data = result.get("chain")
    if chain_data is not None:
        import pandas as pd
        if isinstance(chain_data, pd.DataFrame):
            output["chain"] = df_to_records(chain_data)
        else:
            output["chain"] = chain_data
    else:
        output["chain"] = []

    return output


@router.get("/options/recommend")
@limiter.limit("20/minute")
async def get_options_recommendation(
    request: Request,
    symbol: str = _SYMBOL,
    style: str = _STYLE,
    expiry: Optional[str] = Query(None, description="Expiry date string (optional)"),
    user: dict = Depends(verify_supabase_jwt),
):
    """Get options trade recommendation for a given index symbol."""
    cache_key = f"options-recommend:{symbol}:{style}:{expiry or 'nearest'}"

    try:
        from tools.analyze_options import recommend_option

        result = await cached(
            cache_key,
            ttl=60,
            fn=lambda: recommend_option(symbol, style, expiry),
        )
    except Exception as e:
        log.exception("Options recommendation failed for %s: %s", symbol, e)
        raise HTTPException(status_code=503, detail=f"Market data temporarily unavailable: {e}")

    return clean_dict(result)
