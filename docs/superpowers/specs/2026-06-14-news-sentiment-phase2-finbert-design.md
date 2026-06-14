# News Sentiment Phase 2 — FinBERT Scoring Design Spec

**Date:** 2026-06-14
**Status:** Approved (design); pending implementation plan
**Owner:** Divyanshu
**Builds on:** Phase 1 (`2026-06-14-news-sentiment-predictor-design.md`, shipped to `main`)

## 1. Summary

Phase 1 fetches the right news (Google News by company name, last 30 days) but
scores it with **VADER**, a generic lexicon that misreads financial language
("lower circuit", "SEBI probe", "misses estimates" all read neutral). The result:
a scam-hit, bleeding stock can still read "Neutral". A hand-tuned finance lexicon
was tested and **rejected** — it swung healthy stocks unpredictably (HDFC Bank
flipped +51.8 → −3.7 on identical headlines).

Phase 2 replaces the per-headline scorer with **FinBERT** (`ProsusAI/finbert`),
a model trained on financial text — while keeping the Render backend on its free
instance (no torch on Render). Everything downstream of per-headline scoring
(`aggregate()`, `build_readout()`, the API shape, the UI) is **unchanged**; only
the score each headline receives gets smarter.

## 2. Goals / Non-goals

**Goals**
- FinBERT-quality per-headline sentiment for market, stock, and sector readouts.
- Stay free: no paid APIs, no torch/onnx on the Render free instance.
- Trustworthy on-demand per-stock scores (the Phase 1 pain point) — shipped first.
- Graceful degradation: the feature never breaks when a tier is unavailable.

**Non-goals (Phase 2)**
- No change to `aggregate()` thresholds, confidence math, or `build_readout()` shape.
- No frontend redesign (an optional "scored by" indicator is the only UI touch).
- No nightly per-stock coverage beyond **Nifty 50** (long-tail uses on-demand).
- No self-hosted model server / GPU / paid inference.

## 3. Three-Tier Scoring

For any readout (market scope, stock, or sector), per-headline scores are sourced
in this order; the first available tier wins:

1. **Nightly store (Supabase `sentiment_snapshots`)** — FinBERT-scored readouts
   precomputed in CI for India/world market + Nifty 50 stocks + their sectors.
   Read first → instant, FinBERT-quality, zero per-request cost.
2. **On-demand Hugging Face Inference API** — free hosted FinBERT, called by the
   backend for scopes not in the store (long-tail stocks/sectors). Requires a free
   `HF_TOKEN` env var. Rate-limited; absorbed by tiers 1 and 3.
3. **VADER fallback** — the Phase 1 local scorer. Used when HF has no token, is
   rate-limited, or errors, or when Supabase is unreachable. Always free, always
   available — the feature degrades, never fails.

## 4. FinBERT Score Mapping

`ProsusAI/finbert` returns class probabilities `{positive, negative, neutral}`.
Map each headline to the existing signed per-headline score:

```
score = P(positive) − P(negative)        # in [-1.0, 1.0]
```

This is the same `[-1, 1]` contract `score_texts` already produces, so
`aggregate()` and `build_readout()` consume it unchanged. Neutral-heavy
headlines yield ~0; clearly bearish/bullish headlines yield strong signed values.

## 5. Architecture

### 5.1 Scoring engine (`tools/sentiment_engine.py`)
- Keep `score_texts(texts)` (VADER) as today.
- Add `score_texts_finbert_api(texts) -> list[float]` — calls the HF Inference API
  for `ProsusAI/finbert`, applies the §4 mapping. Needs `HF_TOKEN`. Batches inputs.
  On any failure (no token, non-200, timeout, rate limit) it raises a typed
  `FinbertUnavailable` exception — it does not silently return partial data.
- Add a selector `score_headlines(texts, prefer="finbert") -> (scores, source)`
  that calls `score_texts_finbert_api` when `HF_TOKEN` is set and catches
  `FinbertUnavailable` to fall back to VADER; returns which source was used
  (`"finbert"` | `"vader"`). `build_readout` calls this selector instead of
  `score_texts` directly, and records the `source` on the readout (see §7).
- The **nightly** path uses a separate CI-only FinBERT via `transformers`+`torch`
  (in `tools/requirements-pipeline.txt`), imported **only** by the nightly job —
  never by the backend. A `tools/finbert_local.py` wraps `transformers` lazily.

### 5.2 Supabase store (`tools/sentiment_store.py`)
New helper module mirroring `tools/price_store.py` (same client, env, pagination).
New table `sentiment_snapshots`:

```
sentiment_snapshots(
  id           bigserial primary key,
  scope        text not null,        -- 'market' | 'stock' | 'sector'
  key          text not null,        -- 'india'|'world' | TICKER | sector name
  as_of_date   date not null,        -- the trading date the snapshot covers
  score        real, label text, confidence int, article_count int,
  top_headlines jsonb,               -- same shape build_readout emits
  source       text,                 -- 'finbert'
  computed_at  timestamptz default now(),
  unique (scope, key, as_of_date)
)
```
- Write helpers: `upsert_snapshot(scope, key, readout, as_of_date)` (nightly job).
- Read helpers: `get_snapshot(scope, key) -> readout | None` (latest `as_of_date`,
  backend). Returns `None` on miss / not configured → caller computes on-demand.

### 5.3 Nightly job (extend the EOD pipeline)
Extend `tools/eod_pipeline.py` (and `.github/workflows/eod-pipeline.yml`) — or a
sibling step — to, after market close:
- Resolve the Nifty 50 universe (reuse `tools/stock_lists.py` / `get_stock_meta`
  for names + sectors).
- For India, world, each Nifty 50 stock, and each distinct sector: fetch news
  (existing `fetch_news`), score with **local FinBERT** (`finbert_local`), build the
  readout, and `upsert_snapshot(...)`.
- Throttle Google News fetches (small delay) to avoid rate-limiting ~50–60 requests.
- FinBERT deps live in `tools/requirements-pipeline.txt` (CI only).

### 5.4 Backend endpoints (`backend/routers/sentiment.py`)
- `/sentiment/market`: for each scope, `get_snapshot("market", scope)` first; on
  miss, compute on-demand (fetch → `score_headlines` → `build_readout`).
- `/sentiment/stock`: `get_snapshot("stock", TICKER)` first (covers Nifty 50); on
  miss, compute on-demand via HF→VADER. Sector readout: `get_snapshot("sector",
  sector)` first, else on-demand. Reference market labels read the market snapshots.
- The existing per-request cache (`cached`, 30 min market / 1 h stock) is unchanged
  and sits in front of all of this.

## 6. Graceful Degradation
- No `HF_TOKEN` → on-demand path uses VADER (identical to Phase 1 today).
- Supabase not configured / unreachable → skip tier 1, compute on-demand.
- HF rate-limited / 5xx / timeout → fall back to VADER for that request.
- Nightly job failure → store simply lacks today's rows; backend computes on-demand.
- A stock/sector with no news → existing "insufficient" state (unchanged).

## 7. Transparency (small UI touch)
`build_readout` records `source` (`"finbert"` | `"vader"`) on each readout; the API
returns it. The frontend shows a small, unobtrusive label (e.g. "FinBERT" /
"VADER" chip or footnote) so the user knows which scorer produced a reading. This
is the only frontend change.

## 8. Phasing (two shippable slices)
- **Phase 2a — on-demand FinBERT (ship first):** `score_texts_finbert_api`, the
  `score_headlines` selector, `source` plumbing, HF-token config, VADER fallback,
  and the small UI source label. Closes the on-demand quality gap (Rajesh-style
  stocks) with **no CI or Supabase work**. Verifiable immediately.
- **Phase 2b — nightly store:** `finbert_local`, `sentiment_store`, the
  `sentiment_snapshots` table, the nightly CI step, and read-store-first in the
  endpoints. Adds caching, market + Nifty 50 coverage, and offloads HF.

Each slice is independently shippable and gets its own implementation plan.

## 9. Testing (pytest)
- `score_texts_finbert_api`: mock the HF HTTP response → assert §4 mapping and
  ordering; assert it raises/returns the fallback signal on non-200/timeout.
- `score_headlines` selector: HF path when token set; VADER path + `source="vader"`
  when token absent or HF fails (monkeypatched).
- `sentiment_store`: `upsert_snapshot`/`get_snapshot` against a mocked Supabase
  client; `None` when not configured.
- Endpoints: snapshot-hit path (mock store returns a readout) vs. on-demand miss
  path (store returns `None` → computes). Auth overridden, network mocked.
- Local FinBERT (`finbert_local`) is **mocked** in unit tests — no model download
  in the CI test job; real torch only runs in the nightly job.
- Score-mapping unit test on fixture probabilities (bearish/bullish/neutral).

## 10. Risks & Assumptions
- **HF free tier:** serverless inference for `ProsusAI/finbert` must work with a free
  token and within rate limits. **First build step verifies this**; if unworkable,
  Phase 2a degrades to VADER (no regression) and we lean on Phase 2b nightly FinBERT.
- **Freshness vs. cache:** Nifty 50 names serve last night's FinBERT snapshot during
  the day; long-tail / breaking-news stocks compute live via HF. Acceptable —
  matches how the nightly EOD price store already works.
- **Google News throttling:** ~50–60 nightly fetches need light throttling.

## 11. Out of Scope (later)
- Nightly per-stock coverage beyond Nifty 50.
- Trend-vs-yesterday deltas (now feasible once snapshots accrue — a future add).
- Self-hosted/ONNX inference on the backend (revisit only if HF free tier proves
  insufficient and a paid instance is acceptable).
