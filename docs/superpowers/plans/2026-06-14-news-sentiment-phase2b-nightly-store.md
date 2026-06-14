# News Sentiment Phase 2b — Nightly FinBERT Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Precompute FinBERT sentiment nightly (in free GitHub Actions) for India/world market + the Nifty 50 + their sectors, store it in Supabase, and have the backend read the store first — so common names load instantly with FinBERT quality and on-demand HF calls drop.

**Architecture:** A CI-only local FinBERT scorer (`transformers`/`torch`, never imported by the Render backend) scores headlines in a new nightly job (`tools/sentiment_pipeline.py` + a separate `sentiment-pipeline.yml` workflow), writing readouts to a new Supabase `sentiment_snapshots` table via `tools/sentiment_store.py`. `build_readout` becomes scorer-pluggable so the same assembly serves both the on-demand path (HF/VADER, Phase 2a) and the nightly path (local FinBERT). The backend reads `get_snapshot(...)` first and falls back to on-demand compute on a miss.

**Tech Stack:** Python 3 · `transformers` + `torch` (CPU, CI-only) · Supabase (`supabase-py`) · GitHub Actions · pytest.

**Reference spec:** `docs/superpowers/specs/2026-06-14-news-sentiment-phase2-finbert-design.md` (§3 tier 1, §5.2, §5.3, §5.4, §6, §8 "Phase 2b")

**Builds on:** Phase 2a (on `main`): `score_headlines`, `scored_by`, `tools/sentiment_engine.py`, the stock/sector/market endpoints.

---

## File Structure

**Create:**
- `tools/finbert_local.py` — local FinBERT scorer via `transformers` pipeline. CI-only (heavy deps). Same `P(pos)-P(neg)` mapping as the HF path.
- `tools/sentiment_store.py` — Supabase read/write for `sentiment_snapshots` (mirrors `price_store.py`).
- `tools/sentiment_pipeline.py` — nightly job: compute readouts for market + Nifty 50 + sectors with local FinBERT → upsert.
- `tools/requirements-sentiment.txt` — deps for the nightly job (CI only).
- `.github/workflows/sentiment-pipeline.yml` — nightly workflow (separate from the price EOD job).
- `tests/test_finbert_local.py`, `tests/test_sentiment_store.py`, `tests/test_sentiment_pipeline.py`.

**Modify:**
- `tools/aggregate_sentiment.py` — `build_readout` gains an optional `scorer` param (default unchanged).
- `backend/routers/sentiment.py` — read `get_snapshot` first; fall back to on-demand compute.
- `tests/test_sentiment_aggregate.py` — a test for the pluggable scorer.
- `backend/tests/test_sentiment_router.py` — a snapshot-hit test.
- `README.md`, `workflows/news_sentiment.md` — document the nightly store.

**Manual (one-time):** create the `sentiment_snapshots` table in Supabase (Task 5 DDL).

---

## Task 1: Nightly job dependencies

**Files:** Create `tools/requirements-sentiment.txt`

- [ ] **Step 1: Create the file**

```
feedparser>=6.0.11
vaderSentiment>=3.3.2
requests
yfinance>=0.2.38
transformers>=4.40.0
supabase>=2.3.0
python-dotenv>=1.0.0
```

(Note: `torch` is installed separately in the workflow from the CPU wheel index — see Task 7 — to avoid pulling a huge GPU build.)

- [ ] **Step 2: Commit**

```bash
git add tools/requirements-sentiment.txt
git commit -m "build(sentiment): pipeline deps for nightly FinBERT job"
```

---

## Task 2: Local FinBERT scorer

`tools/finbert_local.py` loads `ProsusAI/finbert` via `transformers` and scores headlines with the same `P(pos)-P(neg)` mapping as the HF path. Lazy model load. Imported ONLY by the nightly job — never by the backend.

**Files:**
- Create: `tools/finbert_local.py`
- Test: `tests/test_finbert_local.py`

- [ ] **Step 1: Write the failing tests**

```python
import tools.finbert_local as fl
from tools.finbert_local import score_texts_finbert_local


def _preds(pos, neg, neu):
    return [
        {"label": "positive", "score": pos},
        {"label": "negative", "score": neg},
        {"label": "neutral", "score": neu},
    ]


def test_local_finbert_maps_pos_minus_neg(monkeypatch):
    # Fake the transformers pipeline: returns a list (per input) of label dicts.
    def fake_pipe(texts, truncation=True):
        return [_preds(0.8, 0.1, 0.1), _preds(0.1, 0.8, 0.1)]
    monkeypatch.setattr(fl, "_get_pipe", lambda: fake_pipe)

    scores = score_texts_finbert_local(["up", "down"])
    assert round(scores[0], 1) == 0.7
    assert round(scores[1], 1) == -0.7


def test_local_finbert_blanks_score_zero(monkeypatch):
    def fake_pipe(texts, truncation=True):
        assert texts == ["real"]
        return [_preds(0.5, 0.3, 0.2)]
    monkeypatch.setattr(fl, "_get_pipe", lambda: fake_pipe)

    scores = score_texts_finbert_local(["", "real", "  "])
    assert scores[0] == 0.0 and scores[2] == 0.0
    assert round(scores[1], 1) == 0.2


def test_local_finbert_empty_input(monkeypatch):
    monkeypatch.setattr(fl, "_get_pipe", lambda: (_ for _ in ()).throw(
        AssertionError("pipe must not be built for empty input")))
    assert score_texts_finbert_local([]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_finbert_local.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.finbert_local'`

- [ ] **Step 3: Implement**

Create `tools/finbert_local.py`:
```python
"""Local FinBERT scoring (transformers + torch). CI / nightly-job use only.

NEVER imported by the FastAPI backend — torch is too heavy for the free
Render instance. The on-demand backend path uses the HF API or VADER instead.
Mapping matches the HF path: P(positive) - P(negative) in [-1, 1].
"""

_pipe = None


def _get_pipe():
    """Lazily build and cache the FinBERT text-classification pipeline."""
    global _pipe
    if _pipe is None:
        from transformers import pipeline
        _pipe = pipeline(
            "text-classification", model="ProsusAI/finbert", top_k=None
        )
    return _pipe


def score_texts_finbert_local(texts: list[str]) -> list[float]:
    """Score each text in [-1, 1] with a locally-run FinBERT model.

    Blank/empty strings score 0.0 without invoking the model (order preserved).
    """
    out = [0.0] * len(texts)
    idx = [i for i, t in enumerate(texts) if t and t.strip()]
    payload = [texts[i] for i in idx]
    if not payload:
        return out

    results = _get_pipe()(payload, truncation=True)
    for j, preds in enumerate(results):
        ls = {p["label"].lower(): float(p["score"]) for p in preds}
        signed = ls.get("positive", 0.0) - ls.get("negative", 0.0)
        out[idx[j]] = max(-1.0, min(1.0, round(signed, 4)))
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_finbert_local.py -v`
Expected: all PASS (the transformers import never runs — `_get_pipe` is monkeypatched).

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/finbert_local.py', doraise=True)"
git add tools/finbert_local.py tests/test_finbert_local.py
git commit -m "feat(sentiment): local FinBERT scorer (CI-only)"
```

---

## Task 3: Make `build_readout` scorer-pluggable

So the nightly job can reuse the exact readout assembly with local FinBERT instead of the HF/VADER selector.

**Files:**
- Modify: `tools/aggregate_sentiment.py`
- Test: `tests/test_sentiment_aggregate.py`

- [ ] **Step 1: Add a failing test (append to `tests/test_sentiment_aggregate.py`)**

```python
def test_build_readout_accepts_custom_scorer():
    def fake_scorer(texts):
        return [0.9] * len(texts), "finbert"
    r = build_readout([_item("a"), _item("b"), _item("c")], scorer=fake_scorer)
    assert r["scored_by"] == "finbert"
    assert r["label"] == "Bullish"   # 0.9 mean -> +90
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sentiment_aggregate.py -k custom_scorer -v`
Expected: FAIL — `TypeError: build_readout() got an unexpected keyword argument 'scorer'`

- [ ] **Step 3: Implement in `tools/aggregate_sentiment.py`**

Change the `build_readout` signature from:
```python
def build_readout(items: list[dict], top_n: int = 6) -> dict:
```
to:
```python
def build_readout(items: list[dict], top_n: int = 6, scorer=score_headlines) -> dict:
```

And change:
```python
    scores, scored_by = score_headlines(texts)
```
to:
```python
    scores, scored_by = scorer(texts)
```

(The default keeps every existing caller — the backend — unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sentiment_aggregate.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/aggregate_sentiment.py', doraise=True)"
git add tools/aggregate_sentiment.py tests/test_sentiment_aggregate.py
git commit -m "feat(sentiment): build_readout accepts a pluggable scorer"
```

---

## Task 4: Supabase snapshot store

`tools/sentiment_store.py` mirrors `tools/price_store.py` (same client setup, `.upsert(...on_conflict).execute()`, paginated reads).

**Files:**
- Create: `tools/sentiment_store.py`
- Test: `tests/test_sentiment_store.py`

- [ ] **Step 1: Write the failing tests (pure converter + helpers via a fake client)**

```python
import tools.sentiment_store as ss
from tools.sentiment_store import readout_to_row


def _readout():
    return {"score": -39.9, "label": "Bearish", "confidence": 80,
            "article_count": 25, "insufficient": False,
            "top_headlines": [{"title": "x", "sentiment": -0.9}],
            "scored_by": "finbert"}


def test_readout_to_row_maps_fields():
    row = readout_to_row("stock", "RELIANCE", _readout(), "2026-06-14")
    assert row["scope"] == "stock"
    assert row["key"] == "RELIANCE"
    assert row["as_of_date"] == "2026-06-14"
    assert row["label"] == "Bearish"
    assert row["score"] == -39.9
    assert row["article_count"] == 25
    assert row["insufficient"] is False
    assert row["scored_by"] == "finbert"
    assert isinstance(row["top_headlines"], list)


class _FakeQuery:
    def __init__(self, data): self._data = data; self.captured = {}
    def upsert(self, rows, on_conflict=None):
        self.captured["rows"] = rows; self.captured["on_conflict"] = on_conflict; return self
    def select(self, *a): return self
    def eq(self, *a): return self
    def order(self, *a, **k): return self
    def limit(self, *a): return self
    def execute(self):
        class R: data = self._data
        return R()


class _FakeClient:
    def __init__(self, data=None): self.q = _FakeQuery(data or [])
    def table(self, name): return self.q


def test_upsert_snapshot_calls_upsert(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(ss, "_client", lambda: fake)
    ss.upsert_snapshot("market", "india", _readout(), "2026-06-14")
    assert fake.q.captured["on_conflict"] == "scope,key,as_of_date"
    assert fake.q.captured["rows"][0]["key"] == "india"


def test_get_snapshot_returns_readout(monkeypatch):
    row = readout_to_row("stock", "RELIANCE", _readout(), "2026-06-14")
    fake = _FakeClient([row])
    monkeypatch.setattr(ss, "_client", lambda: fake)
    monkeypatch.setattr(ss, "is_configured", lambda: True)
    r = ss.get_snapshot("stock", "RELIANCE")
    assert r["label"] == "Bearish"
    assert r["scored_by"] == "finbert"
    assert set(r) >= {"score", "label", "confidence", "article_count",
                      "insufficient", "top_headlines", "scored_by"}


def test_get_snapshot_none_when_not_configured(monkeypatch):
    monkeypatch.setattr(ss, "is_configured", lambda: False)
    assert ss.get_snapshot("stock", "RELIANCE") is None


def test_get_snapshot_none_on_miss(monkeypatch):
    monkeypatch.setattr(ss, "_client", lambda: _FakeClient([]))
    monkeypatch.setattr(ss, "is_configured", lambda: True)
    assert ss.get_snapshot("stock", "NOPE") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sentiment_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.sentiment_store'`

- [ ] **Step 3: Implement**

Create `tools/sentiment_store.py`:
```python
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


_READOUT_KEYS = ("score", "label", "confidence", "article_count",
                 "insufficient", "top_headlines", "scored_by")


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sentiment_store.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/sentiment_store.py', doraise=True)"
git add tools/sentiment_store.py tests/test_sentiment_store.py
git commit -m "feat(sentiment): Supabase snapshot store (read/write)"
```

---

## Task 5: Create the Supabase table (manual, one-time)

**Files:** none (run SQL in the Supabase dashboard).

- [ ] **Step 1: Run this DDL in Supabase → SQL Editor**

```sql
create table if not exists public.sentiment_snapshots (
  id            bigserial primary key,
  scope         text not null,            -- 'market' | 'stock' | 'sector'
  key           text not null,            -- 'india'|'world' | TICKER | sector name
  as_of_date    date not null,
  score         real,
  label         text,
  confidence    int,
  article_count int,
  insufficient  boolean,
  top_headlines jsonb,
  scored_by     text,
  computed_at   timestamptz default now(),
  unique (scope, key, as_of_date)
);
create index if not exists sentiment_snapshots_lookup
  on public.sentiment_snapshots (scope, key, as_of_date desc);
```

- [ ] **Step 2: Confirm** the table exists (Table Editor → `sentiment_snapshots`). No commit — this is infrastructure. Record completion in the task tracker.

---

## Task 6: Nightly pipeline

`tools/sentiment_pipeline.py` computes readouts for market + Nifty 50 + their sectors using local FinBERT and upserts them. Keep the orchestration thin; unit-test the payload-building with everything mocked (no torch, no network, no Supabase).

**Files:**
- Create: `tools/sentiment_pipeline.py`
- Test: `tests/test_sentiment_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
import tools.sentiment_pipeline as sp


def test_targets_includes_market_and_stocks(monkeypatch):
    monkeypatch.setattr(sp, "NIFTY_50", ["RELIANCE", "TCS"])
    monkeypatch.setattr(sp, "get_stock_meta",
                        lambda t: {"name": t.title(), "sector": "Tech"})
    targets = sp.build_targets()
    scopes = {(t["scope"], t["key"]) for t in targets}
    assert ("market", "india") in scopes
    assert ("market", "world") in scopes
    assert ("stock", "RELIANCE") in scopes
    assert ("sector", "Tech") in scopes   # de-duplicated across stocks


def test_run_upserts_each_target(monkeypatch):
    monkeypatch.setattr(sp, "build_targets", lambda: [
        {"scope": "market", "key": "india", "fetch": lambda: [{"title": "t", "summary": "",
         "source": "x", "url": "u", "published_at": "now"}]},
    ])
    captured = []
    monkeypatch.setattr(sp, "upsert_snapshot",
                        lambda scope, key, readout, as_of: captured.append((scope, key, readout["scored_by"])))
    # Force the local-FinBERT scorer to a deterministic stub.
    monkeypatch.setattr(sp, "_local_scorer", lambda texts: ([0.5] * len(texts), "finbert"))
    sp.run(as_of_date="2026-06-14")
    assert captured == [("market", "india", "finbert")]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sentiment_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.sentiment_pipeline'`

- [ ] **Step 3: Implement**

Create `tools/sentiment_pipeline.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sentiment_pipeline.py -v`
Expected: all PASS (no torch/network/Supabase touched — all mocked).

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/sentiment_pipeline.py', doraise=True)"
git add tools/sentiment_pipeline.py tests/test_sentiment_pipeline.py
git commit -m "feat(sentiment): nightly FinBERT precompute pipeline"
```

---

## Task 7: Nightly GitHub Actions workflow

A separate workflow from the price EOD job (keeps torch out of the lean price pipeline).

**Files:** Create `.github/workflows/sentiment-pipeline.yml`

- [ ] **Step 1: Create the workflow**

```yaml
name: Sentiment pipeline

on:
  schedule:
    - cron: "30 11 * * 1-5"   # 17:00 IST — after the EOD price job
  workflow_dispatch:

jobs:
  sentiment:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - name: Install CPU torch + deps
        run: |
          pip install torch --index-url https://download.pytorch.org/whl/cpu
          pip install -r tools/requirements-sentiment.txt
      - name: Run sentiment pipeline
        run: python tools/sentiment_pipeline.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/sentiment-pipeline.yml
git commit -m "ci(sentiment): nightly FinBERT precompute workflow"
```

---

## Task 8: Backend reads the store first

The market / stock / sector readouts check `get_snapshot` before computing on-demand.

**Files:**
- Modify: `backend/routers/sentiment.py`
- Test: `backend/tests/test_sentiment_router.py`

- [ ] **Step 1: Add a snapshot-hit test (append to `backend/tests/test_sentiment_router.py`)**

```python
def test_market_endpoint_uses_snapshot(monkeypatch):
    import tools.sentiment_store as ss

    def fake_snapshot(scope, key):
        return {"score": 55.0, "label": "Bullish", "confidence": 90,
                "article_count": 60, "insufficient": False,
                "top_headlines": [], "scored_by": "finbert"}
    monkeypatch.setattr(ss, "get_snapshot", fake_snapshot)

    res = client.get("/api/v1/sentiment/market")
    assert res.status_code == 200
    body = res.json()
    assert body["india"]["scored_by"] == "finbert"
    assert body["india"]["label"] == "Bullish"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_sentiment_router.py::test_market_endpoint_uses_snapshot -v`
Expected: FAIL — the endpoint computes on-demand (scored_by would be "vader"/"finbert" from live compute, and the label/score won't match the stub) OR an attribute error if `get_snapshot` isn't wired.

- [ ] **Step 3: Implement in `backend/routers/sentiment.py`**

Add a small helper near the top (after the imports):
```python
def _snapshot_or_compute(scope: str, key: str, compute):
    """Return a stored FinBERT snapshot for (scope,key), else compute on-demand."""
    from tools.sentiment_store import get_snapshot
    snap = get_snapshot(scope, key)
    return snap if snap is not None else compute()
```

Change `_scope_readout` from:
```python
def _scope_readout(scope: str) -> dict:
    from tools.fetch_news import fetch_feed_items
    from tools.aggregate_sentiment import build_readout
    return build_readout(fetch_feed_items(scope, limit=60))
```
to:
```python
def _scope_readout(scope: str) -> dict:
    from tools.fetch_news import fetch_feed_items
    from tools.aggregate_sentiment import build_readout
    return _snapshot_or_compute(
        "market", scope, lambda: build_readout(fetch_feed_items(scope, limit=60))
    )
```

In the stock endpoint's `_compute`, wrap the stock and sector readouts:
```python
        stock = _snapshot_or_compute(
            "stock", query, lambda: build_readout(fetch_stock_news(query, name=meta.get("name")))
        )
        industry = (
            _snapshot_or_compute("sector", sector, lambda: build_readout(fetch_sector_news(sector)))
            if sector else None
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_sentiment_router.py -v`
Expected: all PASS (the new snapshot test + the existing 4 — the existing tests monkeypatch fetch funcs and DON'T configure Supabase, so `get_snapshot` returns `None` → they still compute on-demand exactly as before).

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('backend/routers/sentiment.py', doraise=True)"
git add backend/routers/sentiment.py backend/tests/test_sentiment_router.py
git commit -m "feat(sentiment): backend reads nightly snapshot store first"
```

---

## Task 9: Docs

**Files:** Modify `README.md`, `workflows/news_sentiment.md`

- [ ] **Step 1: README** — update the News Sentiment subsection: nightly FinBERT (`ProsusAI/finbert`, local in GitHub Actions) precomputes India/world + Nifty 50 + sectors into Supabase `sentiment_snapshots`; the backend reads the store first and falls back to on-demand HF/VADER on a miss (long-tail stocks). Add `sentiment-pipeline.yml` to the EOD/CI notes and the three new `tools/` files to the structure block. Mark Phase 2 as shipped.

- [ ] **Step 2: workflow SOP** — in `workflows/news_sentiment.md`, document the nightly job (`tools/sentiment_pipeline.py`, `sentiment-pipeline.yml`, 17:00 IST), the `sentiment_snapshots` table, required GitHub secrets (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`), and the read-store-first behaviour. Note the one-time table DDL.

- [ ] **Step 3: Commit**

```bash
git add README.md workflows/news_sentiment.md
git commit -m "docs(sentiment): document nightly FinBERT store (Phase 2b)"
```

---

## Task 10: Final verification

- [ ] **Step 1: Full new + existing suites**

Run: `python -m pytest tests/test_finbert_local.py tests/test_sentiment_store.py tests/test_sentiment_pipeline.py tests/test_sentiment_engine.py tests/test_sentiment_aggregate.py -v && (cd backend && python -m pytest tests/test_sentiment_router.py -v)`
Expected: all PASS.

- [ ] **Step 2: Confirm the backend does NOT import torch**

Run: `cd backend && python -c "import main, sys; assert 'torch' not in sys.modules, 'torch leaked into backend'; print('backend torch-free OK')"`
Expected: prints `backend torch-free OK` (the backend must never load torch — `finbert_local` is only imported by the pipeline).

- [ ] **Step 3: Manual nightly dry-run (once Supabase secrets + table exist)**

Trigger the workflow: GitHub → Actions → "Sentiment pipeline" → Run workflow. Confirm it finishes green and `sentiment_snapshots` has `market`/`stock`/`sector` rows for today. Then load `/dashboard/sentiment` and confirm a Nifty 50 name (e.g. RELIANCE) loads instantly with `scored_by: finbert`.

- [ ] **Step 4: Final commit (if any tweaks remain)**

```bash
git add -A && git commit -m "chore(sentiment): phase 2b verification"
```

---

## Out of Scope (future)
- Per-stock nightly coverage beyond Nifty 50.
- Trend-vs-yesterday deltas (now feasible once snapshots accrue).
- Replacing on-demand HF with a self-hosted/ONNX model.
