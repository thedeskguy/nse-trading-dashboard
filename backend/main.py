import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import get_settings
from services.limiter import limiter
from routers import health, market, analysis, options, payments

_WARM_SYMBOLS = ["NIFTY", "BANKNIFTY", "MIDCPNIFTY"]
_WARM_INTERVAL = 50   # seconds — slightly less than the 55s tool cache TTL


async def _warm_once() -> None:
    """Pre-warm options chain + recommendation cache for all index symbols."""
    try:
        from tools.analyze_options import recommend_option
        from services.cache import cached
        from services.market_hours import adaptive_ttl
        for sym in _WARM_SYMBOLS:
            cache_key = f"options-recommend:{sym}:both:nearest"
            try:
                await cached(
                    cache_key,
                    ttl=adaptive_ttl(60),
                    fn=lambda s=sym: recommend_option(s, "both", None),
                )
            except Exception as e:
                print(f"Cache warm-up warning [{sym}]: {e}")
    except Exception as e:
        print(f"Cache warm-up error: {e}")


async def _background_warmer() -> None:
    """Keep the options cache hot during market hours; sleep longer when closed."""
    from services.market_hours import is_market_open
    while True:
        await _warm_once()
        # Poll more aggressively during market hours, back off when closed
        await asyncio.sleep(_WARM_INTERVAL if is_market_open() else 300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Optional Sentry — no-op when SENTRY_DSN is absent
    settings = get_settings()
    if getattr(settings, "SENTRY_DSN", None):
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1,
        )

    # Warm up Angel One session on startup (best-effort)
    try:
        from services.angel_session import get_angel_session
        await asyncio.to_thread(get_angel_session)
        print("Angel One session ready")
    except Exception as e:
        print(f"Angel One session startup warning: {e}")

    # Start background cache warmer
    warmer = asyncio.create_task(_background_warmer())
    yield
    warmer.cancel()
    try:
        await warmer
    except asyncio.CancelledError:
        pass


app = FastAPI(title="TradeDash API", version="1.0.0", lifespan=lifespan)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(market.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(options.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
