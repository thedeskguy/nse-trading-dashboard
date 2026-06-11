# EOD Data Pipeline + Monetization Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make stock-data retrieval near-instant by persisting daily OHLCV + precomputed scanner signals in Supabase (refreshed nightly by GitHub Actions), and make the paywall flippable via an env flag.

**Architecture:** A nightly GitHub Actions job bulk-downloads EOD bars for Nifty 500 into a Supabase `price_history` table and precomputes all scanner payloads into `scan_results`. The backend gains a store-first read path (`get_daily_df`) shared by signal/ohlcv/confluence/ml-predict/backtest — yfinance is only hit for a cheap 5-day top-up during market hours, or as full fallback when the store is empty. `/market/scan` serves the precomputed payload instantly whenever the market is closed.

**Tech Stack:** FastAPI, Supabase (Postgres via supabase-py — already a backend dep), yfinance, pandas, GitHub Actions, Next.js.

**Context for the implementer:**
- Repo root: `/Users/divyanshuagarwal/Downloads/frist workflow`. Backend lives in `backend/`, shared deterministic scripts in `tools/` (WAT Layer 3). Backend routers add the repo root to `sys.path` and import `tools.*` directly.
- `backend/services/cache.py` exposes `async cached(key, ttl, fn)` — `fn` may be a plain function (run in a thread) **or** an async function (awaited). Redis-backed when Upstash env vars are set, else in-process dict.
- `backend/services/market_hours.py` exposes `is_market_open()` and `adaptive_ttl(base)`.
- After editing any Python file, run `python -c "import py_compile; py_compile.compile('<file>', doraise=True)"` (project rule).
- Backend tests: `cd backend && python -m pytest tests/ -v`. Frontend: `cd frontend && npx tsc --noEmit && npm test`.
- Already done in this codebase (do NOT redo): JWT-fallback gating in `deps.py`, Razorpay webhook idempotency (`webhook_events`), Sentry init in `main.py`, slowapi rate limits, yfinance circuit breaker.

**Manual prerequisites (user actions, flagged in tasks):**
1. Apply `docs/migrations/004_price_history.sql` in the Supabase SQL editor (Task 1).
2. Add GitHub repo secrets `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (Task 8).
3. Trigger the workflow once with `backfill=true` after merge (Task 8).
4. Create a free UptimeRobot monitor on `GET https://<render-backend>/health`, 10-min interval (Task 11) — kills Render free-tier cold starts.

**File map:**
| File | Action | Responsibility |
|---|---|---|
| `docs/migrations/004_price_history.sql` | Create | `price_history` + `scan_results` tables |
| `tools/stock_lists.py` | Create (move) | Single source of NIFTY50/100/200/500 lists |
| `tools/price_store.py` | Create | Supabase read/write for bars + scans |
| `tools/eod_pipeline.py` | Create | Nightly backfill + scan precompute |
| `tools/requirements-pipeline.txt` | Create | Minimal deps for the Actions job |
| `backend/services/daily_data.py` | Create | Store-first `get_daily_df` + resampling |
| `backend/routers/market.py` | Modify | Use store path in signal/ohlcv/scan; import lists |
| `backend/routers/analysis.py` | Modify | Use store path in confluence/ml/backtest |
| `backend/config.py` | Modify | Remove duplicated fields |
| `frontend/src/components/payments/PaywallGate.tsx` | Modify | Env-flag-controlled paywall |
| `frontend/src/lib/api/scanner.ts` | Modify | Optional `precomputed`/`computed_at` fields |
| `.github/workflows/eod-pipeline.yml` | Create | Cron 16:15 IST Mon–Fri |
| `backend/tests/test_price_store.py`, `test_eod_pipeline.py`, `test_daily_data.py`, `test_scan_precomputed.py` | Create | Unit tests |

---

### Task 0: Branch setup

- [ ] **Step 1: Create feature branch per project git workflow**

```bash
cd "/Users/divyanshuagarwal/Downloads/frist workflow"
git checkout develop && git pull
git checkout -b feature/eod-data-pipeline
```

If `develop` doesn't exist locally: `git checkout -b develop origin/develop` first; if no remote `develop` exists at all, branch from `main`.

---

### Task 1: Database migration

**Files:**
- Create: `docs/migrations/004_price_history.sql`

- [ ] **Step 1: Write the migration**

```sql
-- 004_price_history.sql — persistent EOD OHLCV store + precomputed scanner results.
-- Written by the nightly GitHub Actions pipeline (service-role key); read by the backend.
-- RLS enabled with NO policies: only the service-role key (which bypasses RLS) can access.

create table if not exists price_history (
  ticker  text not null,
  date    date not null,
  open    double precision not null,
  high    double precision not null,
  low     double precision not null,
  close   double precision not null,
  volume  bigint not null,
  primary key (ticker, date)
);

create index if not exists idx_price_history_ticker_date
  on price_history (ticker, date desc);

create table if not exists scan_results (
  index_name  text primary key,
  computed_at timestamptz not null default now(),
  payload     jsonb not null
);

alter table price_history enable row level security;
alter table scan_results enable row level security;
```

- [ ] **Step 2: Commit**

```bash
git add docs/migrations/004_price_history.sql
git commit -m "feat(db): add price_history + scan_results tables for EOD pipeline"
```

- [ ] **Step 3: ⚠️ MANUAL — tell the user to paste this SQL into the Supabase SQL editor and run it.** The backend degrades gracefully without it (falls back to live fetch), but the pipeline job will fail until applied.

---

### Task 2: Move stock lists to `tools/stock_lists.py`

The NIFTY constituent lists currently live in `backend/routers/market.py` (lines 26 → the end of the `STOCK_LISTS` dict). The pipeline job needs them without importing FastAPI.

**Files:**
- Create: `tools/stock_lists.py`
- Modify: `backend/routers/market.py`

- [ ] **Step 1: Create `tools/stock_lists.py`**

Header:

```python
"""
NSE index constituent lists (WAT Layer 3 data module).

Single source of truth for NIFTY50/100/200/500, used by both the FastAPI
backend (/market/scan) and tools/eod_pipeline.py.
Synced with NSE India on 2026-04-18.
"""
```

Then **cut** (not copy) the following block from `backend/routers/market.py` and paste it verbatim below the header. The block starts at the comment `# Current Nifty 50 constituents — synced with NSE India on 2026-04-18` and ends with the closing `}` of the `STOCK_LISTS: dict[str, list] = {...}` dict (it contains, in order: `NIFTY_50`, `_NIFTY_NEXT_50`, `_NIFTY_MIDCAP_100`, `_NIFTY_SMALLMID_300`, the `_dedup` helper, `NIFTY_100`/`NIFTY_200`/`NIFTY_500`, and `STOCK_LISTS`). Do **not** move `_INDICES` — that stays in `market.py`.

- [ ] **Step 2: Add the import in `market.py`**

Where the block was removed, the file should go straight from the `router = APIRouter()` line to `_INDICES = [...]`. Add below the existing imports (after `from services.serializers import df_to_records`):

```python
from tools.stock_lists import STOCK_LISTS
```

- [ ] **Step 3: Compile-check both files and run backend tests**

```bash
python -c "import py_compile; py_compile.compile('tools/stock_lists.py', doraise=True)"
python -c "import py_compile; py_compile.compile('backend/routers/market.py', doraise=True)"
cd backend && python -m pytest tests/ -v && cd ..
```

Expected: all existing tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tools/stock_lists.py backend/routers/market.py
git commit -m "refactor: move NIFTY constituent lists to tools/stock_lists.py"
```

---

### Task 3: `tools/price_store.py`

**Files:**
- Create: `tools/price_store.py`
- Test: `backend/tests/test_price_store.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_price_store.py
import sys, os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # repo root

from tools.price_store import df_to_rows, rows_to_df


def _sample_df():
    idx = pd.to_datetime(["2026-06-08", "2026-06-09", "2026-06-10"])
    return pd.DataFrame({
        "Open":   [100.0, 101.0, 102.0],
        "High":   [101.5, 102.5, 103.5],
        "Low":    [99.5, 100.5, 101.5],
        "Close":  [101.0, 102.0, 103.0],
        "Volume": [1000, 1100, 1200],
    }, index=idx)


def test_df_to_rows_shape():
    rows = df_to_rows("RELIANCE.NS", _sample_df())
    assert len(rows) == 3
    assert rows[0] == {
        "ticker": "RELIANCE.NS", "date": "2026-06-08",
        "open": 100.0, "high": 101.5, "low": 99.5, "close": 101.0, "volume": 1000,
    }


def test_round_trip():
    df = _sample_df()
    out = rows_to_df(df_to_rows("X.NS", df))
    pd.testing.assert_frame_equal(out, df, check_dtype=False)


def test_rows_to_df_empty():
    assert rows_to_df([]).empty
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_price_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.price_store'`

- [ ] **Step 3: Implement `tools/price_store.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_price_store.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add tools/price_store.py backend/tests/test_price_store.py
git commit -m "feat: Supabase price store for daily OHLCV + precomputed scans"
```

---

### Task 4: `tools/eod_pipeline.py`

**Files:**
- Create: `tools/eod_pipeline.py`
- Test: `backend/tests/test_eod_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_eod_pipeline.py
import sys, os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))  # repo root

from tools.eod_pipeline import build_scan_payload


def _synthetic_df(rows=80, seed=42):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end="2026-06-10", periods=rows)
    close = 100 + np.cumsum(rng.normal(0, 1, rows))
    return pd.DataFrame({
        "Open": close + rng.normal(0, 0.5, rows),
        "High": close + 1.5,
        "Low": close - 1.5,
        "Close": close,
        "Volume": rng.integers(1000, 5000, rows),
    }, index=idx)


def test_build_scan_payload_signals_and_missing():
    history = {"AAA.NS": _synthetic_df()}
    payload = build_scan_payload([("AAA.NS", "Alpha"), ("BBB.NS", "Beta")], history)
    assert len(payload) == 2
    a, b = payload
    assert a["ticker"] == "AAA.NS" and a["signal"] in ("BUY", "SELL", "HOLD")
    assert isinstance(a["change_pct"], float)
    assert a["last_price"] is not None
    # ticker with no history degrades to None fields, not an exception
    assert b["signal"] is None and b["last_price"] is None and b["change_pct"] is None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_eod_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.eod_pipeline'`

- [ ] **Step 3: Implement `tools/eod_pipeline.py`**

```python
"""
Nightly EOD pipeline (WAT Layer 3).

1. Bulk-download daily OHLCV for Nifty 500 from yfinance (chunked, throttled).
2. Upsert bars into Supabase `price_history`.
3. Recompute scanner signals for NIFTY50/100/200/500 into `scan_results`.

Run from repo root:
    python tools/eod_pipeline.py              # daily top-up (1mo window)
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
    period = "5y" if args.backfill else "1mo"
    print(f"Refreshing {len(tickers)} tickers, period={period}")
    refresh_prices(tickers, period)

    # Signals need ~3 months of bars; daily runs only fetched 1mo, so read the
    # scan window back from the store.
    print("Loading 120-day window for scan computation…")
    history = price_store.get_history_bulk(tickers, days=120)

    for index_name, stock_list in STOCK_LISTS.items():
        payload = build_scan_payload(stock_list, history)
        price_store.upsert_scan(index_name, payload)
        ok = sum(1 for r in payload if r["signal"])
        print(f"{index_name}: scan stored ({ok}/{len(payload)} with signals)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_eod_pipeline.py tests/test_price_store.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tools/eod_pipeline.py backend/tests/test_eod_pipeline.py
git commit -m "feat: nightly EOD pipeline — backfill prices + precompute scans"
```

---

### Task 5: `backend/services/daily_data.py`

**Files:**
- Create: `backend/services/daily_data.py`
- Test: `backend/tests/test_daily_data.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_daily_data.py
import asyncio
import sys, os
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))             # repo root

import services.daily_data as daily_data
from services.daily_data import get_daily_df, last_expected_session, resample_ohlcv


def _daily_df(end, rows=30):
    idx = pd.bdate_range(end=end, periods=rows)
    close = np.linspace(100, 110, rows)
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1,
                         "Close": close, "Volume": [1000] * rows}, index=idx)


def test_resample_weekly():
    df = _daily_df("2026-06-05", rows=10)  # two full Mon-Fri weeks
    wk = resample_ohlcv(df, "W-FRI")
    assert len(wk) == 2
    first = df.iloc[:5]
    assert wk["Open"].iloc[0] == first["Open"].iloc[0]
    assert wk["High"].iloc[0] == first["High"].max()
    assert wk["Low"].iloc[0] == first["Low"].min()
    assert wk["Close"].iloc[0] == first["Close"].iloc[-1]
    assert wk["Volume"].iloc[0] == first["Volume"].sum()


def test_last_expected_session_weekend():
    sat = datetime(2026, 6, 13, 12, 0, tzinfo=daily_data._IST)  # Saturday
    assert last_expected_session(sat).weekday() == 4             # -> Friday


def test_store_hit_no_live_fetch(monkeypatch):
    fresh = _daily_df(pd.Timestamp(last_expected_session()))
    from tools import price_store
    monkeypatch.setattr(price_store, "is_configured", lambda: True)
    monkeypatch.setattr(price_store, "get_history", lambda t, d: fresh)
    monkeypatch.setattr(daily_data, "is_market_open", lambda: False)

    import tools.fetch_stock_data as fsd

    def _boom(*a, **k):
        raise AssertionError("live fetch should not happen on a fresh store hit")

    monkeypatch.setattr(fsd, "_fetch_yfinance", _boom)
    monkeypatch.setattr(fsd, "fetch_ohlcv", _boom)

    df = asyncio.run(get_daily_df("TESTHIT.NS", "3mo"))
    assert len(df) == len(fresh)


def test_store_miss_falls_back(monkeypatch):
    from tools import price_store
    monkeypatch.setattr(price_store, "is_configured", lambda: True)
    monkeypatch.setattr(price_store, "get_history", lambda t, d: pd.DataFrame())

    fallback = _daily_df("2026-06-10")
    import tools.fetch_stock_data as fsd
    monkeypatch.setattr(fsd, "fetch_ohlcv", lambda *a, **k: fallback)

    df = asyncio.run(get_daily_df("TESTMISS.NS", "3mo"))
    assert len(df) == len(fallback)
```

(Tickers are unique per test so the shared `cached()` store can't cross-contaminate.)

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_daily_data.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.daily_data'`

- [ ] **Step 3: Implement `backend/services/daily_data.py`**

```python
"""
Store-first daily OHLCV access, shared by /market/signal, /market/ohlcv,
/analysis/confluence, /analysis/ml-predict and /analysis/backtest.

Read order:
  1. Supabase price_history (filled nightly by tools/eod_pipeline.py)
  2. + cheap 5-day yfinance top-up when the market is open or the store lags
  3. Full yfinance/Angel fetch only when the store has nothing for the ticker.
"""
import asyncio
from datetime import date, datetime, time as dtime, timedelta, timezone

import pandas as pd

from services.cache import cached
from services.logger import get_logger
from services.market_hours import adaptive_ttl, is_market_open

log = get_logger(__name__)

_IST = timezone(timedelta(hours=5, minutes=30))

# period -> calendar days (margin included for weekends/holidays)
PERIOD_DAYS = {
    "1mo": 35, "3mo": 100, "6mo": 190, "1y": 380,
    "2y": 745, "5y": 1840, "10y": 3700, "ytd": 380, "max": 7400,
}

_OHLC_AGG = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample daily bars to weekly ('W-FRI') or monthly ('ME') candles."""
    out = df.resample(rule).agg(_OHLC_AGG)
    return out.dropna(subset=["Open", "High", "Low", "Close"])


def last_expected_session(now: datetime | None = None) -> date:
    """Most recent NSE session date. Ignores exchange holidays — a false
    'stale' on a holiday just triggers one cheap 5-day fetch."""
    now = now.astimezone(_IST) if now else datetime.now(_IST)
    d = now.date()
    if now.time() < dtime(9, 15):
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _normalize_daily_index(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance daily bars come tz-aware; the store's are naive. Align them."""
    df = df.copy()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index = df.index.normalize()
    return df


async def get_daily_df(ticker: str, period: str) -> pd.DataFrame:
    """Daily OHLCV for `ticker` covering `period`, store-first. Cached."""
    cache_key = f"dailydf:{ticker}:{period}"

    async def _load():
        days = PERIOD_DAYS.get(period, 380)
        df = pd.DataFrame()
        try:
            from tools import price_store
            if price_store.is_configured():
                df = await asyncio.to_thread(price_store.get_history, ticker, days)
        except Exception as e:
            log.warning("price store read failed for %s: %s", ticker, e)

        if df.empty:
            from tools.fetch_stock_data import fetch_ohlcv
            return await asyncio.to_thread(fetch_ohlcv, ticker, "1d", period)

        stale = df.index[-1].date() < last_expected_session()
        if is_market_open() or stale:
            try:
                from tools.fetch_stock_data import _fetch_yfinance
                recent = await asyncio.to_thread(_fetch_yfinance, ticker, "1d", "5d")
                recent = _normalize_daily_index(recent)
                df = pd.concat([df[~df.index.isin(recent.index)], recent]).sort_index()
            except Exception as e:
                log.warning("live top-up failed for %s: %s", ticker, e)
        return df

    return await cached(cache_key, ttl=adaptive_ttl(300), fn=_load)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_daily_data.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/daily_data.py backend/tests/test_daily_data.py
git commit -m "feat(backend): store-first get_daily_df with live top-up + resampling"
```

---

### Task 6: Wire routers onto the store-first path

**Files:**
- Modify: `backend/routers/market.py` (`get_signal` ~line 589, `get_ohlcv` ~line 453)
- Modify: `backend/routers/analysis.py` (`get_ml_prediction`, `get_confluence`, `get_backtest`)

Note: `cached()` accepts async functions directly (it awaits them), so the pattern below — async closure that awaits `get_daily_df` then runs CPU work in a thread — keeps cache keys and TTLs identical to today.

- [ ] **Step 1: `market.py` — rewrite `get_signal`'s try-block**

Replace:

```python
    try:
        from tools.fetch_stock_data import fetch_ohlcv
        from tools.compute_indicators import compute_all
        from tools.generate_signals import generate_signal

        def _compute():
            df = fetch_ohlcv(ticker, interval, period)
            df = compute_all(df)
            return generate_signal(df)

        signal = await cached(cache_key, ttl=adaptive_ttl(300), fn=_compute)
```

with:

```python
    try:
        from services.daily_data import get_daily_df
        from tools.compute_indicators import compute_all
        from tools.generate_signals import generate_signal

        async def _compute():
            if interval == "1d":
                df = await get_daily_df(ticker, period)
            else:
                from tools.fetch_stock_data import fetch_ohlcv
                df = await asyncio.to_thread(fetch_ohlcv, ticker, interval, period)
            return await asyncio.to_thread(lambda: generate_signal(compute_all(df.copy())))

        signal = await cached(cache_key, ttl=adaptive_ttl(300), fn=_compute)
```

- [ ] **Step 2: `market.py` — rewrite `get_ohlcv`'s try-block**

Replace:

```python
    try:
        from tools.fetch_stock_data import fetch_ohlcv

        def _fetch():
            df = fetch_ohlcv(ticker, interval, period)
            if with_indicators:
                from tools.compute_indicators import (
                    compute_emas, compute_bollinger, compute_rsi,
                    compute_macd, compute_obv,
                )
                df = compute_emas(df, [9, 21, 50, 200])
                df = compute_bollinger(df, period=20, std=2.0)
                df = compute_rsi(df, period=14)
                df = compute_macd(df)
                df = compute_obv(df)
            return df

        df = await cached(cache_key, ttl=adaptive_ttl(300), fn=_fetch)
```

with:

```python
    try:
        async def _fetch():
            if interval == "1d":
                from services.daily_data import get_daily_df
                df = (await get_daily_df(ticker, period)).copy()
            else:
                from tools.fetch_stock_data import fetch_ohlcv
                df = await asyncio.to_thread(fetch_ohlcv, ticker, interval, period)
            if with_indicators:
                from tools.compute_indicators import (
                    compute_emas, compute_bollinger, compute_rsi,
                    compute_macd, compute_obv,
                )

                def _ind(d):
                    d = compute_emas(d, [9, 21, 50, 200])
                    d = compute_bollinger(d, period=20, std=2.0)
                    d = compute_rsi(d, period=14)
                    d = compute_macd(d)
                    return compute_obv(d)

                df = await asyncio.to_thread(_ind, df)
            return df

        df = await cached(cache_key, ttl=adaptive_ttl(300), fn=_fetch)
```

- [ ] **Step 3: `analysis.py` — add `import pandas as pd` to the top imports** (after `import asyncio`), then rewrite the three endpoints:

**`get_ml_prediction`** — replace its try-block fetch/predict code:

```python
    try:
        from services.daily_data import get_daily_df
        from tools.compute_indicators import compute_all
        from tools.ml_predictor import train_and_predict

        async def _predict():
            df = await get_daily_df(ticker, period)
            return await asyncio.to_thread(lambda: train_and_predict(compute_all(df.copy())))

        prediction = await cached(cache_key, ttl=3600, fn=_predict)
```

**`get_confluence`** — delete the `_CONFLUENCE_TIMEFRAMES` list and replace `_compute_all` with (summary code below it stays unchanged):

```python
    async def _compute_all():
        from services.daily_data import get_daily_df, resample_ohlcv
        from tools.compute_indicators import compute_all
        from tools.generate_signals import generate_signal

        # One 5y daily fetch; 1W/1M candles are resampled from it instead of
        # three separate yfinance downloads.
        daily = await get_daily_df(ticker, "5y")

        def _signal_rows():
            two_years = daily[daily.index >= daily.index[-1] - pd.DateOffset(years=2)]
            frames = [
                ("1D", daily.tail(63).copy()),           # ~3 months of sessions
                ("1W", resample_ohlcv(two_years, "W-FRI")),
                ("1M", resample_ohlcv(daily, "ME")),
            ]
            rows = []
            for label, frame in frames:
                try:
                    sig = generate_signal(compute_all(frame))
                    rows.append({
                        "timeframe": label,
                        "signal": sig["signal"],
                        "confidence": sig["confidence"],
                        "components": {
                            k: {"points": v["points"], "label": v["signal"]}
                            for k, v in sig["components"].items()
                        },
                    })
                except Exception as e:
                    log.exception("Confluence %s %s failed: %s", ticker, label, e)
                    rows.append({"timeframe": label, "signal": None,
                                 "confidence": None, "components": {}})
            return rows

        return await asyncio.to_thread(_signal_rows)
```

**`get_backtest`** — replace its try-block fetch/run code:

```python
    try:
        from services.daily_data import get_daily_df
        from tools.compute_indicators import compute_all
        from tools.backtester import run_backtest

        async def _run():
            df = await get_daily_df(ticker, period)
            return await asyncio.to_thread(lambda: run_backtest(compute_all(df.copy())))

        result = await cached(cache_key, ttl=adaptive_ttl(21600), fn=_run)
```

- [ ] **Step 4: Compile-check + full backend test run**

```bash
python -c "import py_compile; py_compile.compile('backend/routers/market.py', doraise=True)"
python -c "import py_compile; py_compile.compile('backend/routers/analysis.py', doraise=True)"
cd backend && python -m pytest tests/ -v && cd ..
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/market.py backend/routers/analysis.py
git commit -m "perf(backend): signal/ohlcv/confluence/ml/backtest read from price store"
```

Behavior note (intentional): confluence 1W/1M candles are now resampled from daily bars instead of fetched natively — values can differ marginally from yfinance's own weekly/monthly bars.

---

### Task 7: Precomputed `/market/scan`

**Files:**
- Modify: `backend/routers/market.py` (`scan_stocks`, ~line 624)
- Modify: `frontend/src/lib/api/scanner.ts`
- Test: `backend/tests/test_scan_precomputed.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_scan_precomputed.py
import sys, os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))             # repo root

from fastapi.testclient import TestClient

import main
from deps import verify_supabase_jwt
import routers.market as market
from tools import price_store


def test_scan_returns_precomputed_when_market_closed(monkeypatch):
    main.app.dependency_overrides[verify_supabase_jwt] = lambda: {"user_id": "u1", "email": "t@t.t"}
    try:
        monkeypatch.setattr(market, "is_market_open", lambda: False)
        payload = [{"ticker": "RELIANCE.NS", "name": "Reliance", "signal": "BUY",
                    "confidence": 80, "last_price": 2900.0, "change_pct": 1.2}]
        monkeypatch.setattr(
            price_store, "get_scan",
            lambda idx: {"payload": payload,
                         "computed_at": datetime.now(timezone.utc).isoformat()},
        )
        # TestClient without context manager: lifespan (Angel warm-up) is skipped
        client = TestClient(main.app)
        res = client.get("/api/v1/market/scan?index=NIFTY50")
        assert res.status_code == 200
        body = res.json()
        assert body["precomputed"] is True
        assert body["stocks"] == payload
        assert body["index"] == "NIFTY50"
    finally:
        main.app.dependency_overrides.clear()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_scan_precomputed.py -v`
Expected: FAIL — response JSON has no `precomputed` key (the endpoint runs the live scan path).

- [ ] **Step 3: Add the precomputed branch in `scan_stocks`**

In `backend/routers/market.py`, directly after `cache_key = f"scan:{index.lower()}"` and before `async def _do_scan():`, insert:

```python
    # When the market is closed, serve the nightly precomputed scan — instant,
    # zero upstream calls. The live scan path only runs during trading hours.
    if not is_market_open():
        try:
            from tools import price_store
            pre = await asyncio.to_thread(price_store.get_scan, index)
            if pre and pre.get("payload"):
                computed_at = pre.get("computed_at")
                age_ok = True
                if computed_at:
                    from datetime import datetime, timedelta, timezone
                    dt = datetime.fromisoformat(computed_at.replace("Z", "+00:00"))
                    age_ok = datetime.now(timezone.utc) - dt < timedelta(days=4)
                if age_ok:
                    return {
                        "stocks": pre["payload"],
                        "count": len(pre["payload"]),
                        "index": index,
                        "precomputed": True,
                        "computed_at": computed_at,
                    }
        except Exception as e:
            log.warning("precomputed scan unavailable for %s: %s", index, e)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all PASS (new test included).

- [ ] **Step 5: Add the optional fields to the frontend scan type**

In `frontend/src/lib/api/scanner.ts`, find the `ScanResponse` interface and add two optional fields:

```ts
  precomputed?: boolean;
  computed_at?: string | null;
```

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/market.py backend/tests/test_scan_precomputed.py frontend/src/lib/api/scanner.ts
git commit -m "perf(scan): serve nightly precomputed scan when market is closed"
```

---

### Task 8: GitHub Actions nightly workflow

**Files:**
- Create: `tools/requirements-pipeline.txt`
- Create: `.github/workflows/eod-pipeline.yml`

- [ ] **Step 1: Create `tools/requirements-pipeline.txt`**

```
pandas>=2.0.0
numpy>=1.26.0
yfinance>=0.2.38
supabase>=2.3.0
python-dotenv>=1.0.0
```

(`tools/fetch_stock_data.py` imports the backend circuit breaker inside a try/except ImportError, and Angel One only inside `fetch_ohlcv` — neither is needed by the pipeline, so this minimal set is sufficient.)

- [ ] **Step 2: Create `.github/workflows/eod-pipeline.yml`**

```yaml
name: EOD price pipeline

on:
  schedule:
    - cron: "45 10 * * 1-5"   # 16:15 IST — after NSE close (15:30 IST)
  workflow_dispatch:
    inputs:
      backfill:
        description: "Full 5y backfill (first run / repair)"
        type: boolean
        default: false

jobs:
  eod:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r tools/requirements-pipeline.txt
      - name: Run pipeline
        run: python tools/eod_pipeline.py ${{ inputs.backfill == true && '--backfill' || '' }}
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
```

- [ ] **Step 3: Commit**

```bash
git add tools/requirements-pipeline.txt .github/workflows/eod-pipeline.yml
git commit -m "ci: nightly EOD pipeline workflow (16:15 IST Mon-Fri)"
```

- [ ] **Step 4: ⚠️ MANUAL — tell the user:**
  1. Add repo secrets `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (GitHub → Settings → Secrets → Actions).
  2. After merge, run the workflow once manually with `backfill: true` (Actions tab → "EOD price pipeline" → Run workflow). Expect ~10–15 min.

---

### Task 9: `config.py` duplicate-field cleanup

**Files:**
- Modify: `backend/config.py:31-37`

- [ ] **Step 1: Remove the duplicated block**

`ALLOW_UNVERIFIED_JWT`, `SENTRY_DSN`, and `model_config` are each defined twice. Replace:

```python
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # Set to "1" only in local dev when SUPABASE_URL is intentionally absent.
    # Never set in production — a misconfigured deploy would auth any well-formed token.
    ALLOW_UNVERIFIED_JWT: str = "0"
    SENTRY_DSN: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

with:

```python
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

(The first definitions at the top of the class — `ALLOW_UNVERIFIED_JWT: str = "0"` and `SENTRY_DSN: Optional[str] = None` — stay. Move the two comment lines about local-dev usage up to sit above that first `ALLOW_UNVERIFIED_JWT` definition.)

- [ ] **Step 2: Verify + commit**

```bash
python -c "import py_compile; py_compile.compile('backend/config.py', doraise=True)"
cd backend && python -m pytest tests/ -v && cd ..
git add backend/config.py
git commit -m "chore(config): remove duplicated settings fields"
```

---

### Task 10: Flag-controlled paywall

**Files:**
- Modify: `frontend/src/components/payments/PaywallGate.tsx` (currently a 10-line pass-through)
- Modify: `frontend/.env.example`

The original gate UI exists in git history (commit `ced898c`); this restores it behind a build-time flag so ending the free beta is a Vercel env change + redeploy, not a code change.

- [ ] **Step 1: Replace `PaywallGate.tsx` entirely with:**

```tsx
"use client";
import { useSubscription } from "@/lib/api/payments";
import { UpgradeModal } from "./UpgradeModal";
import { Skeleton } from "@/components/ui/skeleton";
import { Lock } from "lucide-react";

interface PaywallGateProps {
  feature?: string; // e.g. "Options Dashboard"
  children: React.ReactNode;
}

// Free beta: flag off = gate bypassed. Set NEXT_PUBLIC_PAYWALL_ENABLED=true in
// Vercel and redeploy to end the beta (NEXT_PUBLIC_ vars are inlined at build).
const PAYWALL_ENABLED = process.env.NEXT_PUBLIC_PAYWALL_ENABLED === "true";

export function PaywallGate({ feature = "this feature", children }: PaywallGateProps) {
  if (!PAYWALL_ENABLED) return <>{children}</>;
  return <GatedContent feature={feature}>{children}</GatedContent>;
}

function GatedContent({ feature, children }: { feature: string; children: React.ReactNode }) {
  const { data, isLoading } = useSubscription();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }

  if (data?.plan === "pro") {
    return <>{children}</>;
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 p-8 text-center">
      <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
        <Lock className="w-7 h-7 text-primary" />
      </div>
      <div className="space-y-2 max-w-sm">
        <h2 className="font-display text-xl font-semibold">Pro Feature</h2>
        <p className="text-muted-foreground text-sm leading-relaxed">
          {feature} is available on the Pro plan. Upgrade to get access to live options
          chain data, OI analysis, and trade recommendations.
        </p>
      </div>
      <UpgradeModal />
    </div>
  );
}
```

(`UpgradeModal` takes no props — verified against the original implementation in commit `ced898c`. The hook lives in a child component so it isn't called conditionally.)

- [ ] **Step 2: Add to `frontend/.env.example`:**

```
# Set to "true" to enable the Pro paywall (ends free beta). Build-time flag.
NEXT_PUBLIC_PAYWALL_ENABLED=false
```

- [ ] **Step 3: Verify**

```bash
cd frontend && npx tsc --noEmit && npm test
```

Expected: no type errors, existing tests PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/payments/PaywallGate.tsx frontend/.env.example
git commit -m "feat(payments): restore paywall behind NEXT_PUBLIC_PAYWALL_ENABLED flag"
```

---

### Task 11: Docs

**Files:**
- Modify: `README.md`
- Modify: `PLAN.md`

- [ ] **Step 1: README** — add a section under the architecture/usage area:

```markdown
## EOD Data Pipeline

Daily OHLCV for Nifty 500 + precomputed scanner signals are persisted in Supabase
(`price_history`, `scan_results`) by `.github/workflows/eod-pipeline.yml`
(16:15 IST, Mon–Fri). Backend endpoints read the store first and only hit
yfinance for a 5-day top-up during market hours, or as full fallback.

- First run / repair: Actions → "EOD price pipeline" → Run workflow → backfill: true
- Local run: `python tools/eod_pipeline.py --backfill` (needs SUPABASE_URL +
  SUPABASE_SERVICE_ROLE_KEY in `.env`)
- Required GitHub secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

### Keeping the Render free instance warm

Render's free plan sleeps after ~15 min idle (≈50 s cold start). Create a free
[UptimeRobot](https://uptimerobot.com) HTTP monitor on `GET /health` at a 10-minute
interval, or upgrade to Render Starter.
```

Also update the README file-structure listing with `tools/stock_lists.py`, `tools/price_store.py`, `tools/eod_pipeline.py`, `backend/services/daily_data.py`.

- [ ] **Step 2: PLAN.md** — in Phase 11 P1, mark **"Persist historical OHLCV"** as `[x]` with a note: "Done via Supabase price_history + nightly GitHub Actions pipeline (`tools/eod_pipeline.py`); scanner precomputed in scan_results."

- [ ] **Step 3: Commit**

```bash
git add README.md PLAN.md
git commit -m "docs: EOD pipeline, keep-warm setup, PLAN.md status update"
```

---

### Final verification (before merging to develop)

- [ ] `cd backend && python -m pytest tests/ -v` — all pass
- [ ] `cd frontend && npx tsc --noEmit && npm test` — clean
- [ ] `cd frontend && npm run build` — builds
- [ ] Manual smoke (needs `.env` with Supabase creds): `python tools/eod_pipeline.py` against a test ticker subset, then `GET /api/v1/market/scan?index=NIFTY50` outside market hours returns `"precomputed": true`
- [ ] Open PR `feature/eod-data-pipeline` → `develop` per project git workflow
