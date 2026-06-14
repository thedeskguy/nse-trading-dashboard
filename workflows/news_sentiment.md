# News Sentiment Workflow

## Objective
Produce free, real-time news-sentiment readouts — stock, India market, and world market — for the dashboard's Market Sentiment page. Three independent readouts; never blended.

## Inputs
- **Market sentiment:** scope = `india` or `world`
- **Stock sentiment:** NSE ticker (e.g. `RELIANCE`)

## Tool Sequence
```
tools/fetch_news.py          →  list of headlines + metadata
tools/sentiment_engine.py    →  per-headline score (FinBERT via HF, else VADER)
tools/aggregate_sentiment.py →  build_readout() → score / label / confidence + top headlines
```

1. `fetch_news.py` — market scopes pull free RSS feeds (Moneycontrol, Economic Times, Business Standard, LiveMint for India; MarketWatch, CNBC, Reuters for world). Per-stock (`fetch_stock_news`) primarily uses a free **Google News RSS search** by the company **name** (resolved via yfinance), restricted to the **last 30 days** (`when:30d`) so it reflects the latest news, plus the market RSS pool. If `NEWS_API_KEY` is set, also enriches via GNews free tier; absent → RSS/Google-News only.
2. `fetch_news.fetch_sector_news(sector)` — industry/sector news for the stock view via Google News (`Indian {sector} sector stocks`, last 30 days). The company name + sector are resolved per ticker by `fetch_fundamentals.get_stock_meta(ticker)` (yfinance); unknown sector → industry readout omitted.
3. `sentiment_engine.score_headlines()` — scores each headline. Prefers **FinBERT** (`ProsusAI/finbert`) via the Hugging Face Inference API when `HF_TOKEN` is set; falls back to local **VADER** when absent or on any failure. Returns the scorer used (`finbert` | `vader`).
4. `aggregate_sentiment.py` — `build_readout(headlines)` returns `{score, label, confidence, top_headlines}`.

## Endpoints
| Endpoint | Description |
|---|---|
| `GET /api/v1/sentiment/market?scope=india` | India market sentiment readout |
| `GET /api/v1/sentiment/market?scope=world` | World market sentiment readout |
| `GET /api/v1/sentiment/stock?ticker=RELIANCE` | Stock-specific sentiment readout |

## How to Test

**Tool unit tests:**
```bash
python -m pytest tests/test_sentiment_aggregate.py tests/test_fetch_news.py
```

**Endpoint tests:**
```bash
cd backend && python -m pytest tests/test_sentiment_router.py
```

## Config
| Variable | Required | Notes |
|---|---|---|
| `NEWS_API_KEY` | No | GNews free-tier key; absent → RSS-only feeds |
| `HF_TOKEN` | No | Free Hugging Face token; enables FinBERT scoring, absent → VADER |

VADER runs locally and is the guaranteed fallback when FinBERT (HF Inference API) is unavailable.

## Edge Cases
- **Insufficient news** (`< 3` usable articles after fetch) → readout returns a low-confidence Neutral with label `"Insufficient recent news"`. No score is fabricated.
- **Dead RSS feed** — each feed is fetched independently; failures are caught and skipped. A dead feed never raises or blocks other feeds.
- **Missing `NEWS_API_KEY`** — GNews enrichment is skipped silently; RSS-only path is the default and fully functional.

## Nightly FinBERT store (Phase 2b — built)
- **Job:** `tools/sentiment_pipeline.py`, run by `.github/workflows/sentiment-pipeline.yml` (17:00 IST, Mon–Fri; after the EOD price job). Installs CPU `torch` + `tools/requirements-sentiment.txt`.
- **What it does:** scores India/world market + the **Nifty 50** + their sectors with **local FinBERT** (`tools/finbert_local.py`, transformers/torch — CI only, never on the Render backend) and upserts readouts to Supabase `sentiment_snapshots` via `tools/sentiment_store.py`.
- **Backend read path:** `routers/sentiment.py` calls `sentiment_store.get_snapshot(scope, key)` first; on a miss (long-tail stock, or Supabase not configured) it computes on-demand (HF FinBERT → VADER).
- **Required GitHub secrets:** `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (already used by the EOD price pipeline).
- **One-time setup:** create the `sentiment_snapshots` table (see the Phase 2b plan's DDL), then trigger the workflow manually once (Actions → "Sentiment pipeline" → Run workflow).

## Future
- **Trend deltas** — compare today's score against yesterday's snapshot to surface sentiment momentum (snapshots now accrue, so this is feasible).
- **Wider nightly coverage** — beyond Nifty 50.
