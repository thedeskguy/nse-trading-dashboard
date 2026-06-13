# News Sentiment Predictor — Design Spec

**Date:** 2026-06-14
**Status:** Approved (design); pending implementation plan
**Owner:** Divyanshu

## 1. Summary

A new **Market Sentiment** feature for the NSE/BSE trading SaaS that derives an
**upside/downside bias** for a stock from recent news sentiment, alongside
broader **India market** and **world market** sentiment. It runs entirely on
**free, local** tooling — no paid sentiment/news APIs.

The three sentiment readouts (stock / India / world) are **independent and never
mathematically combined**. The stock's own news sentiment *is* its upside/downside
call; India and world are shown as side-by-side context so the user can judge
alignment themselves.

This is framed as a **sentiment bias, not investment advice or a price target**,
consistent with the project's existing "decision-support only" disclaimer.

## 2. Goals / Non-goals

**Goals**
- A dedicated `/sentiment` page in the Next.js frontend.
- Always-on India + world market sentiment (precomputed nightly, kept fresh).
- On-demand per-stock sentiment for any searched ticker.
- Zero paid APIs; free RSS backbone + optional free-tier news API enrichment.
- Quality scoring via FinBERT nightly (in free CI compute) + fast VADER live top-up.

**Non-goals (v1)**
- No mathematical blending of the three scores into one number.
- No nightly per-stock batch (per-stock is on-demand only).
- No historical sentiment charts / time-series.
- No alerts/notifications.
- No regional-language NLP — **English only**.
- No feed into the existing composite Confidence / BUY-HOLD-SELL engine.

## 3. User Experience

Route: `frontend/src/app/sentiment/page.tsx`

**Top — market context (always populated):**
- Two gauges: **India Market** and **World Market**.
- Each shows: label (Bullish / Neutral / Bearish), score (−100…+100),
  trend vs. previous day, confidence, and the top headlines driving it
  (each headline with its own sentiment + source + timestamp).
- "As of <time>" freshness indicator.

**Below — per-stock drill-down (on-demand):**
- Stock search (reuse existing unified stock search).
- On select → **stock sentiment card**: the stock's own news sentiment as the
  headline upside/downside call (score / label / confidence), the headlines
  behind it, plus small **reference chips** repeating India + world labels so
  the user can eyeball alignment (e.g. "stock Bullish, world Bearish").
- If too few articles → **"Insufficient recent news"** state with low confidence;
  never a fabricated signal.

## 4. Scoring Logic

One aggregation function, applied **independently** to each of the three news sets.

**Per-headline score:** `[-1, +1]`
- Live path: **VADER** (lexicon, instant, always available).
- Authoritative daily path: **FinBERT** (finance-tuned, nightly in CI).

**Aggregation (`headlines → score / label / confidence`):**
- `score` = mean per-headline sentiment, scaled to `[-100, +100]`.
  v1 uses a simple mean; recency-weighting (newer headlines count more) is a
  documented future tweak, not built in v1.
- `label`: Bullish (`> +20`), Neutral (`-20…+20`), Bearish (`< -20`).
  Thresholds are named constants.
- `confidence` = f(article count, agreement). Few articles **or** highly
  conflicting headlines → low confidence. Below a minimum article count
  (e.g. `< 3`) → "insufficient news", confidence forced low.

All thresholds/constants centralized and documented so they are easy to defend
and tune.

## 5. Architecture

Follows the WAT framework (Workflows → Agents → Tools) and existing patterns.

### 5.1 Tools (Layer 3 — `tools/`)
- **`fetch_news.py`** — pull free RSS feeds:
  - India: Moneycontrol, Economic Times, Business Standard, LiveMint.
  - World: Reuters, CNBC.
  - Optional free-tier API (GNews / NewsAPI) for ticker-specific enrichment
    **only if** an API key is present in env; otherwise RSS-only (graceful).
  - Dedupe + normalize to `{title, summary, source, url, published_at}`. Cached.
- **`sentiment_engine.py`** — one interface, two backends:
  `score_vader(texts)` (live) and `score_finbert(texts)` (nightly, heavy).
  FinBERT/torch imported lazily so the live path never loads it.
- **`aggregate_sentiment.py`** — the `headlines → score/label/confidence`
  function (§4), run per scope. No cross-scope weighting.
- **`sentiment_store.py`** — Supabase read/write helpers for the new table
  (mirrors the existing `price_store.py` pattern).

### 5.2 Nightly precompute (extend existing EOD pipeline)
- Extend `tools/eod_pipeline.py` + `.github/workflows/eod-pipeline.yml`
  (runs 16:15 IST, Mon–Fri). FinBERT runs here in **free GitHub Actions
  compute — never on Render**.
- Computes **India + world** market sentiment and writes to new Supabase table
  `sentiment_snapshots`:
  `(id, scope, ticker, score, label, confidence, top_headlines jsonb, computed_at)`
  where `scope ∈ {india, world}` (ticker null in v1; the `ticker` column is
  reserved for future per-stock FinBERT caching).
- FinBERT deps live in `tools/requirements-pipeline.txt` (CI only), not the
  backend/root requirements.

### 5.3 Backend (FastAPI — `backend/`)
- New router `backend/routers/sentiment.py`:
  - `GET /api/v1/sentiment/market` → India + world. Reads Supabase
    `sentiment_snapshots`; if stale, does a live VADER top-up.
  - `GET /api/v1/sentiment/stock?ticker=…` → on-demand: fetch ticker news
    (RSS pool filter by company name + optional API query) → VADER live →
    stock readout. (Per-stock is VADER-only in v1; FinBERT is market-scope
    nightly only.)
- Uses the existing `backend/services/cache.py` and serializer patterns.
- No paid API; free-tier news key optional via env, absence handled gracefully.

### 5.4 Frontend (Next.js — `frontend/`)
- `src/app/sentiment/page.tsx` + components: market gauge, headline list,
  stock sentiment card, reference chips. Reuse the existing design system /
  theming. Add nav entry to the sentiment page.

## 6. Caching & Cost Control
- **Market sentiment:** nightly precompute + live VADER refresh at most every
  ~30 min during market hours.
- **Per-ticker sentiment:** cache ~1h (mirrors the options-token cache pattern).
- **FinBERT:** only ever executes in CI; the backend never downloads/loads it.

## 7. Edge Cases
- No / too few articles → "Insufficient recent news", low confidence, no signal.
- An RSS source is down → skip it, degrade gracefully.
- No free-tier API key → RSS-only.
- Stale Supabase snapshot → show "as of <time>" + attempt live top-up.
- Conflicting headlines → reflected as low confidence.
- English-only; non-English items filtered out in v1.

## 8. Testing (pytest, `tests/`)
- Aggregation: score scaling, label thresholds, confidence vs. article
  count/agreement, "insufficient news" path.
- `fetch_news`: dedupe/normalize; graceful degradation when a feed or the API
  key is missing.
- VADER scoring on fixture headlines (golden cases incl. "misses estimates").
- **FinBERT is mocked** in unit tests — no model download in the CI test job.
- Follow existing `tests/` conventions; run `pytest tests/` before pushing.

## 9. Phasing
1. **Phase 1:** tools (`fetch_news`, `sentiment_engine` VADER path,
   `aggregate_sentiment`), backend `/sentiment/market` + `/sentiment/stock`
   on VADER only, frontend page. Ships a usable feature with no CI changes.
2. **Phase 2:** FinBERT nightly in the EOD pipeline + `sentiment_snapshots`
   table + `sentiment_store.py`; backend reads Supabase first.
3. **Phase 3 (future, out of scope now):** historical sentiment charts, alerts,
   optional feed into the composite signal.

## 10. Disclaimer
The feature presents a **news-sentiment bias only** — not financial advice,
not a price prediction, not a solicitation. Surfaced in the UI per the existing
project disclaimer language.
