import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import get_settings
from services.limiter import limiter
from routers import health, market, analysis, options, payments


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
        import asyncio
        await asyncio.to_thread(get_angel_session)
        print("Angel One session ready")
    except Exception as e:
        print(f"Angel One session startup warning: {e}")
    yield


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
