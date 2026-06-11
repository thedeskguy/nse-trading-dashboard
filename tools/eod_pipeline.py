"""
Nightly EOD pipeline (WAT Layer 3).

1. Bulk-download daily OHLCV for Nifty 500 from yfinance (chunked, throttled).
2. Upsert bars into Supabase `price_history`.
3. Recompute scanner signals for NIFTY50/100/200/500 into `scan_results`.

Run from repo root:
    python tools/eod_pipeline.py              # daily top-up (3mo window)
    python tools/eod_pipeline.py --backfill   # full 5y backfill (first run)

Scheduled by .github/workflows/eod-pipeline.yml at 16:15 IST, Mon-Fri.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.stock_lists import STOCK_LISTS  # noqa: E402
from tools import price_store              # noqa: E402

CHUNK = 50          # tickers per yf.download call
SLEEP_BETWEEN = 2   # seconds between chunks — stays under Yahoo's rate limits


def refresh_prices(tickers: list[str], period: str) -> dict:
    """Download daily bars and upsert them. Returns ticker -> DataFrame."""
    from tools.fetch_stock_data import fetch_yfinance_bulk

    fetched: dict = {}
    failed: list[str] = []
    for i in range(0, len(tickers), CHUNK):
        chunk = tickers[i:i + CHUNK]
        try:
            frames = fetch_yfinance_bulk(chunk, "1d", period)
        except ValueError as e:
            print(f"chunk {i // CHUNK + 1}: bulk fetch failed entirely: {e}")
            frames = {}
        for ticker, df in frames.items():
            price_store.upsert_history(ticker, df)
            fetched[ticker] = df
        failed.extend(t for t in chunk if t not in frames)
        print(f"chunk {i // CHUNK + 1}: {len(frames)}/{len(chunk)} tickers stored")
        time.sleep(SLEEP_BETWEEN)
    if failed:
        print(f"WARNING: no data for {len(failed)} tickers: {failed[:20]}")
    return fetched


def build_scan_payload(stock_list: list, history: dict) -> list[dict]:
    """Compute signal rows for one index list from pre-loaded daily history. Pure."""
    from tools.compute_indicators import compute_all
    from tools.generate_signals import generate_signal

    out = []
    for ticker, name in stock_list:
        row = {"ticker": ticker, "name": name, "signal": None,
               "confidence": None, "last_price": None, "change_pct": None}
        df = history.get(ticker)
        if df is not None and len(df) >= 2:
            try:
                prev = float(df["Close"].iloc[-2])
                last = float(df["Close"].iloc[-1])
                sig = generate_signal(compute_all(df.copy()))
                row.update(
                    signal=sig["signal"],
                    confidence=sig["confidence"],
                    last_price=sig["last_price"],
                    change_pct=round((last - prev) / prev * 100, 2),
                )
            except Exception as e:
                print(f"scan compute failed for {ticker}: {e}")
        out.append(row)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="EOD price + scan pipeline")
    parser.add_argument("--backfill", action="store_true", help="full 5y backfill")
    args = parser.parse_args()

    if not price_store.is_configured():
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")

    tickers = [t for t, _ in STOCK_LISTS["NIFTY500"]]
    # Daily runs fetch 3mo (not just the new day) so the store self-heals after
    # pipeline outages of up to ~3 months without a manual backfill.
    period = "5y" if args.backfill else "3mo"
    print(f"Refreshing {len(tickers)} tickers, period={period}")
    refresh_prices(tickers, period)

    # Signals need ~3 months of bars — read the scan window back from the store.
    print("Loading 120-day window for scan computation…")
    history = price_store.get_history_bulk(tickers, days=120)
    short = sum(1 for df in history.values() if len(df) < 60)
    if short:
        print(f"WARNING: {short} tickers have <60 bars in the scan window "
              "(new listings or store gaps) — their signals may be weak or None")

    for index_name, stock_list in STOCK_LISTS.items():
        payload = build_scan_payload(stock_list, history)
        price_store.upsert_scan(index_name, payload)
        ok = sum(1 for r in payload if r["signal"])
        print(f"{index_name}: scan stored ({ok}/{len(payload)} with signals)")


if __name__ == "__main__":
    main()
