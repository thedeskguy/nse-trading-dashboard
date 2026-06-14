"""Supabase store for nightly FinBERT sentiment snapshots.

Mirrors tools/price_store.py. Written by tools/sentiment_pipeline.py (nightly
GitHub Actions job); read by backend/routers/sentiment.py. Credentials:
SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.
"""
import os


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


def _client():
    _load_env()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
    from supabase import create_client
    return create_client(url, key)


def readout_to_row(scope: str, key: str, readout: dict, as_of_date: str) -> dict:
    """A build_readout() result -> a sentiment_snapshots row."""
    return {
        "scope": scope,
        "key": key,
        "as_of_date": as_of_date,
        "score": readout["score"],
        "label": readout["label"],
        "confidence": readout["confidence"],
        "article_count": readout["article_count"],
        "insufficient": readout["insufficient"],
        "top_headlines": readout["top_headlines"],
        "scored_by": readout.get("scored_by"),
    }


def _row_to_readout(row: dict) -> dict:
    return {
        "score": row["score"],
        "label": row["label"],
        "confidence": row["confidence"],
        "article_count": row["article_count"],
        "insufficient": row["insufficient"],
        "top_headlines": row.get("top_headlines") or [],
        "scored_by": row.get("scored_by"),
    }


def upsert_snapshot(scope: str, key: str, readout: dict, as_of_date: str) -> None:
    _client().table("sentiment_snapshots").upsert(
        [readout_to_row(scope, key, readout, as_of_date)],
        on_conflict="scope,key,as_of_date",
    ).execute()


def get_snapshot(scope: str, key: str) -> dict | None:
    """Most recent stored readout for (scope, key), or None on miss / not configured."""
    if not is_configured():
        return None
    try:
        res = (
            _client().table("sentiment_snapshots")
            .select("*")
            .eq("scope", scope).eq("key", key)
            .order("as_of_date", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    if not res.data:
        return None
    return _row_to_readout(res.data[0])
