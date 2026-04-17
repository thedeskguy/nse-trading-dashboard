import sys
import os

# Ensure backend/ is on the path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import health, market, analysis, options, payments


@asynccontextmanager
async def lifespan(app: FastAPI):
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
