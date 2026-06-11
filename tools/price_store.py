"""
Supabase-backed persistent store for daily OHLCV bars and precomputed scanner results.

WAT Layer 3 — deterministic execution. Used by:
  - tools/eod_pipeline.py                (GitHub Actions nightly job — writes)
  - backend/services/daily_data.py and backend/routers/market.py (reads)

Credentials: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from env.
For local dev, .env at repo root and backend/.env are loaded as fallbacks.
"""
import os
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

import pandas as pd

_PAGE = 1000          # PostgREST caps responses at 1000 rows — paginate beyond that
_UPSERT_BATCH = 1000  # rows per upsert request


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(root, ".env"))
    load_dotenv(os.path.join(root, "backend", ".env"))


def is_configured() -> bool:
    _load_env()
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))


@lru_cache(maxsize=1)
def _client():
    _load_env()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
    from supabase import create_client
    return create_client(url, key)


# ── pure converters (unit-tested, no network) ────────────────────────────────
def df_to_rows(ticker: str, df: pd.DataFrame) -> list[dict]:
    """OHLCV DataFrame (DatetimeIndex) -> price_history rows."""
    rows = []
    for idx, r in df.iterrows():
        rows.append({
            "ticker": ticker,
            "date": idx.date().isoformat(),
            "open": float(r["Open"]),
            "high": float(r["High"]),
            "low": float(r["Low"]),
            "close": float(r["Close"]),
            "volume": int(r["Volume"]),
        })
    return rows


def rows_to_df(rows: list[dict]) -> pd.DataFrame:
    """price_history rows -> OHLCV DataFrame matching fetch_ohlcv()'s shape."""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                            "close": "Close", "volume": "Volume"})
    df.index.name = None
    return df[["Open", "High", "Low", "Close", "Volume"]]


# ── price_history ─────────────────────────────────────────────────────────────
def upsert_history(ticker: str, df: pd.DataFrame) -> int:
    rows = df_to_rows(ticker, df)
    for i in range(0, len(rows), _UPSERT_BATCH):
        _client().table("price_history").upsert(
            rows[i:i + _UPSERT_BATCH], on_conflict="ticker,date"
        ).execute()
    return len(rows)


def get_history(ticker: str, days: int) -> pd.DataFrame:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows: list[dict] = []
    page = 0
    while True:
        res = (
            _client().table("price_history")
            .select("date,open,high,low,close,volume")
            .eq("ticker", ticker).gte("date", cutoff)
            .order("date")
            .range(page * _PAGE, (page + 1) * _PAGE - 1)
            .execute()
        )
        rows.extend(res.data)
        if len(res.data) < _PAGE:
            break
        page += 1
    return rows_to_df(rows)


def get_history_bulk(tickers: list[str], days: int) -> dict[str, pd.DataFrame]:
    """History for many tickers in few requests (used by the pipeline)."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    by_ticker: dict[str, list[dict]] = {}
    for i in range(0, len(tickers), 20):
        chunk = tickers[i:i + 20]
        page = 0
        while True:
            res = (
                _client().table("price_history")
                .select("ticker,date,open,high,low,close,volume")
                .in_("ticker", chunk).gte("date", cutoff)
                .order("ticker").order("date")
                .range(page * _PAGE, (page + 1) * _PAGE - 1)
                .execute()
            )
            for row in res.data:
                by_ticker.setdefault(row["ticker"], []).append(row)
            if len(res.data) < _PAGE:
                break
            page += 1
    return {t: rows_to_df(r) for t, r in by_ticker.items()}


# ── scan_results ──────────────────────────────────────────────────────────────
def upsert_scan(index_name: str, payload: list[dict]) -> None:
    _client().table("scan_results").upsert({
        "index_name": index_name,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }, on_conflict="index_name").execute()


def get_scan(index_name: str) -> dict | None:
    """Returns {"payload": [...], "computed_at": "..."} or None."""
    res = (
        _client().table("scan_results")
        .select("payload,computed_at")
        .eq("index_name", index_name).limit(1).execute()
    )
    return res.data[0] if res.data else None
