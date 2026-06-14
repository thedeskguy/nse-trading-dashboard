# News Sentiment Workflow

## Objective
Produce free, real-time news-sentiment readouts — stock, India market, and world market — for the dashboard's Market Sentiment page. Three independent readouts; never blended.

## Inputs
- **Market sentiment:** scope = `india` or `world`
- **Stock sentiment:** NSE ticker (e.g. `RELIANCE`)

## Tool Sequence
```
tools/fetch_news.py          →  list of headlines + metadata
tools/sentiment_engine.py    →  per-headline VADER score
tools/aggregate_sentiment.py →  build_readout() → score / label / confidence + top headlines
```

1. `fetch_news.py` — market scopes pull free RSS feeds (Moneycontrol, Economic Times, Business Standard, LiveMint for India; MarketWatch, CNBC, Reuters for world). Per-stock (`fetch_stock_news`) primarily uses a free **Google News RSS search** (`{symbol} share price NSE`, India-localized) plus the market RSS pool. If `NEWS_API_KEY` is set, also enriches via GNews free tier; absent → RSS/Google-News only.
2. `sentiment_engine.py` — applies the VADER lexicon to each headline locally (no API call, no cost).
3. `aggregate_sentiment.py` — `build_readout(headlines)` returns `{score, label, confidence, top_headlines}`.

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

No other API keys needed. VADER runs locally.

## Edge Cases
- **Insufficient news** (`< 3` usable articles after fetch) → readout returns a low-confidence Neutral with label `"Insufficient recent news"`. No score is fabricated.
- **Dead RSS feed** — each feed is fetched independently; failures are caught and skipped. A dead feed never raises or blocks other feeds.
- **Missing `NEWS_API_KEY`** — GNews enrichment is skipped silently; RSS-only path is the default and fully functional.

## Phase 2 (upcoming — not yet built)
- **FinBERT nightly scoring** — transformer-based sentiment precomputed in the GitHub Actions EOD pipeline (16:15 IST, Mon–Fri), stored in a Supabase `sentiment_snapshots` table. Backend reads snapshots; VADER live scoring remains as intraday fallback.
- **Trend deltas** — compare today's score against yesterday's snapshot to surface sentiment momentum.
