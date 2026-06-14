"""Nightly FinBERT sentiment precompute (GitHub Actions).

Scores India/world market + the Nifty 50 + their sectors with LOCAL FinBERT
and upserts readouts into Supabase `sentiment_snapshots`. The backend reads
that store first; misses are computed on-demand (HF/VADER).
"""
import sys
import os
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.stock_lists import NIFTY_50
from tools.fetch_news import fetch_feed_items, fetch_stock_news, fetch_sector_news
from tools.fetch_fundamentals import get_stock_meta
from tools.aggregate_sentiment import build_readout
from tools.finbert_local import score_texts_finbert_local
from tools.sentiment_store import upsert_snapshot, is_configured

_THROTTLE_S = 1.0   # be gentle on Google News across ~50+ fetches


def _local_scorer(texts):
    return score_texts_finbert_local(texts), "finbert"


def build_targets() -> list[dict]:
    """Each target: {scope, key, fetch} where fetch() -> news items."""
    targets: list[dict] = [
        {"scope": "market", "key": "india", "fetch": lambda: fetch_feed_items("india", limit=60)},
        {"scope": "market", "key": "world", "fetch": lambda: fetch_feed_items("world", limit=60)},
    ]
    seen_sectors: set[str] = set()
    for symbol in NIFTY_50:
        meta = get_stock_meta(f"{symbol}.NS")
        name, sector = meta.get("name"), meta.get("sector")
        targets.append({
            "scope": "stock", "key": symbol,
            "fetch": (lambda s=symbol, n=name: fetch_stock_news(s, name=n)),
        })
        if sector and sector not in seen_sectors:
            seen_sectors.add(sector)
            targets.append({
                "scope": "sector", "key": sector,
                "fetch": (lambda sec=sector: fetch_sector_news(sec)),
            })
    return targets


def run(as_of_date: str | None = None) -> int:
    as_of_date = as_of_date or date.today().isoformat()
    targets = build_targets()
    ok = 0
    for t in targets:
        try:
            items = t["fetch"]()
            readout = build_readout(items, scorer=_local_scorer)
            upsert_snapshot(t["scope"], t["key"], readout, as_of_date)
            ok += 1
            print(f"stored {t['scope']}:{t['key']} -> {readout['label']} ({readout['score']})")
        except Exception as e:
            print(f"FAILED {t['scope']}:{t['key']}: {e}")
        time.sleep(_THROTTLE_S)
    return ok


def main() -> None:
    if not is_configured():
        print("Supabase not configured (SUPABASE_URL / SERVICE_ROLE_KEY). Aborting.")
        raise SystemExit(1)
    stored = run()
    print(f"sentiment pipeline done: {stored} snapshots")


if __name__ == "__main__":
    main()
