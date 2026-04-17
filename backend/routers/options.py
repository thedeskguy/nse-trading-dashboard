import sys
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from deps import verify_supabase_jwt
from services.cache import cached
from services.serializers import df_to_records, clean_dict

router = APIRouter()


@router.get("/options/chain")
async def get_options_chain(
    symbol: str = Query(..., description="Index symbol: NIFTY, BANKNIFTY, or MIDCPNIFTY"),
    expiry: Optional[str] = Query(None, description="Expiry date string (optional, defaults to nearest)"),
    user: dict = Depends(verify_supabase_jwt),
):
    """Fetch live options chain for a given index symbol."""
    cache_key = f"options-chain:{symbol}:{expiry or 'nearest'}"

    try:
        from tools.fetch_options_chain import fetch_options_chain
        import pandas as pd

        def _fetch():
            return fetch_options_chain(symbol, expiry)

        result = await cached(cache_key, ttl=60, fn=_fetch)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Market data temporarily unavailable: {e}")

    # Serialize the chain DataFrame if present
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
async def get_options_recommendation(
    symbol: str = Query(..., description="Index symbol: NIFTY, BANKNIFTY, or MIDCPNIFTY"),
    style: str = Query("both", description="Trade style: intraday, positional, or both"),
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
        raise HTTPException(status_code=503, detail=f"Market data temporarily unavailable: {e}")

    return clean_dict(result)
