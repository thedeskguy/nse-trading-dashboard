# News Sentiment Predictor — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a usable News Sentiment page that shows India + world market sentiment and on-demand per-stock sentiment, computed live with free RSS + VADER (no paid APIs, no CI changes).

**Architecture:** Three independent readouts (stock / India / world), never blended. New Python tools at repo root (`tools/fetch_news.py`, `tools/sentiment_engine.py`, `tools/aggregate_sentiment.py`) do fetch → score → aggregate. A new FastAPI router (`backend/routers/sentiment.py`) exposes `/sentiment/market` and `/sentiment/stock`, reusing the existing `cached()` service. The Next.js dashboard gets a new authed page + react-query hook. FinBERT/Supabase nightly precompute is **Phase 2** (separate plan) — not in scope here.

**Tech Stack:** Python 3 · FastAPI · `feedparser` (RSS) · `vaderSentiment` (lexicon scoring) · pytest · Next.js (App Router) · TanStack Query · TypeScript.

**Reference spec:** `docs/superpowers/specs/2026-06-14-news-sentiment-predictor-design.md`

---

## File Structure

**Create:**
- `tools/sentiment_engine.py` — VADER per-headline scoring. One responsibility: text → sentiment number.
- `tools/aggregate_sentiment.py` — pure aggregation (`aggregate`) + readout assembly (`build_readout`). Thresholds + confidence math live here.
- `tools/fetch_news.py` — RSS fetch + normalize/dedupe/filter helpers + optional free-tier API enrichment.
- `backend/routers/sentiment.py` — `/sentiment/market` and `/sentiment/stock` endpoints.
- `frontend/src/lib/api/sentiment.ts` — typed react-query hooks.
- `frontend/src/app/dashboard/sentiment/page.tsx` — the page.
- `frontend/src/components/sentiment/SentimentGauge.tsx` — one market/stock readout card.
- `frontend/src/components/sentiment/HeadlineList.tsx` — headline rows with per-headline sentiment.
- `tests/test_sentiment_aggregate.py` — aggregation + readout unit tests.
- `tests/test_fetch_news.py` — normalize/dedupe/filter + graceful-degradation tests.
- `backend/tests/test_sentiment_router.py` — endpoint smoke tests (TestClient + auth override).

**Modify:**
- `backend/requirements.txt` — add `feedparser`, `vaderSentiment`.
- `backend/main.py:15,109` — import + register the sentiment router.
- `frontend/src/components/layout/Sidebar.tsx` + `MobileNav.tsx` — add a "Sentiment" nav entry (mirror existing items).
- `README.md` — document the new feature.
- `workflows/` — add `news_sentiment.md` SOP.

**Route note:** The spec wrote `/sentiment`; the authed app lives under `/dashboard/*`, so the real route is `/dashboard/sentiment`, consistent with `stocks`, `options`, `scanner`.

---

## Task 1: Add Python dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Append the two libraries**

Add these lines to the end of `backend/requirements.txt`:

```
feedparser>=6.0.11
vaderSentiment>=3.3.2
```

- [ ] **Step 2: Install into the active venv**

Run: `pip install "feedparser>=6.0.11" "vaderSentiment>=3.3.2"`
Expected: `Successfully installed feedparser-... vaderSentiment-...`

- [ ] **Step 3: Verify both import**

Run: `python -c "import feedparser, vaderSentiment.vaderSentiment as v; print('ok')"`
Expected: prints `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "build: add feedparser + vaderSentiment for news sentiment"
```

---

## Task 2: VADER scoring engine

`tools/sentiment_engine.py` exposes one function: `score_texts(texts) -> list[float]`, each in `[-1.0, 1.0]` (VADER compound). FinBERT is Phase 2 and intentionally absent.

**Files:**
- Create: `tools/sentiment_engine.py`
- Test: `tests/test_sentiment_aggregate.py` (shared test file; engine tests live here too)

- [ ] **Step 1: Write the failing test**

Create `tests/test_sentiment_aggregate.py`:

```python
from tools.sentiment_engine import score_texts


def test_score_texts_signs():
    scores = score_texts([
        "Company posts record profit, beats estimates",   # positive
        "Shares crash as firm misses targets and cuts guidance",  # negative
    ])
    assert len(scores) == 2
    assert scores[0] > 0
    assert scores[1] < 0
    assert all(-1.0 <= s <= 1.0 for s in scores)


def test_score_texts_empty_and_blank():
    assert score_texts([]) == []
    assert score_texts(["", "   "]) == [0.0, 0.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sentiment_aggregate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.sentiment_engine'`

- [ ] **Step 3: Write minimal implementation**

Create `tools/sentiment_engine.py`:

```python
"""Free, local sentiment scoring.

Phase 1: VADER lexicon scoring only (instant, no model download, no API).
FinBERT (nightly, heavy) is added in Phase 2 behind the same module.
"""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def score_texts(texts: list[str]) -> list[float]:
    """Return the VADER compound score in [-1, 1] for each text.

    Blank/empty strings score 0.0. Order is preserved.
    """
    out: list[float] = []
    for t in texts:
        if not t or not t.strip():
            out.append(0.0)
            continue
        out.append(float(_analyzer.polarity_scores(t)["compound"]))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sentiment_aggregate.py -v`
Expected: both tests PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/sentiment_engine.py', doraise=True)"
git add tools/sentiment_engine.py tests/test_sentiment_aggregate.py
git commit -m "feat(sentiment): VADER scoring engine"
```

---

## Task 3: Aggregation — score, label, confidence

Pure function `aggregate(per_headline)`. Centralizes all magic numbers.

**Files:**
- Create: `tools/aggregate_sentiment.py`
- Test: `tests/test_sentiment_aggregate.py` (append)

- [ ] **Step 1: Write the failing tests (append to the test file)**

Add to `tests/test_sentiment_aggregate.py`:

```python
from tools.aggregate_sentiment import (
    aggregate, BULLISH_THRESHOLD, BEARISH_THRESHOLD, MIN_ARTICLES,
)


def test_aggregate_bullish_label_and_range():
    r = aggregate([0.8, 0.6, 0.7, 0.5])
    assert r["article_count"] == 4
    assert r["insufficient"] is False
    assert r["score"] > BULLISH_THRESHOLD
    assert r["label"] == "Bullish"
    assert 0 <= r["confidence"] <= 100


def test_aggregate_bearish_label():
    r = aggregate([-0.7, -0.5, -0.6, -0.8])
    assert r["label"] == "Bearish"
    assert r["score"] < BEARISH_THRESHOLD


def test_aggregate_neutral_band():
    r = aggregate([0.05, -0.05, 0.0, 0.02])
    assert r["label"] == "Neutral"
    assert BEARISH_THRESHOLD <= r["score"] <= BULLISH_THRESHOLD


def test_aggregate_insufficient_articles_forces_neutral_low_confidence():
    r = aggregate([0.9, 0.8])  # fewer than MIN_ARTICLES
    assert MIN_ARTICLES == 3
    assert r["insufficient"] is True
    assert r["label"] == "Neutral"
    assert r["confidence"] <= 20


def test_aggregate_empty():
    r = aggregate([])
    assert r["article_count"] == 0
    assert r["insufficient"] is True
    assert r["score"] == 0.0
    assert r["label"] == "Neutral"
    assert r["confidence"] == 0


def test_aggregate_conflicting_lowers_confidence():
    agree = aggregate([0.6, 0.6, 0.6, 0.6, 0.6])
    conflict = aggregate([0.6, -0.6, 0.6, -0.6, 0.6])
    assert conflict["confidence"] < agree["confidence"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sentiment_aggregate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.aggregate_sentiment'`

- [ ] **Step 3: Write minimal implementation**

Create `tools/aggregate_sentiment.py`:

```python
"""Aggregate per-headline sentiment into one readout.

The SAME function is applied independently to each scope (stock / india /
world). Nothing is blended across scopes — that is a product decision in the
design spec, not an implementation detail to revisit here.
"""

# Score thresholds on a -100..+100 scale.
BULLISH_THRESHOLD = 20.0
BEARISH_THRESHOLD = -20.0
# Below this many articles we refuse to emit a directional call.
MIN_ARTICLES = 3
# Confidence ramps to full at this many articles.
CONFIDENCE_FULL_AT = 10
# Confidence ceiling when there are too few articles.
INSUFFICIENT_CONFIDENCE_CAP = 20


def _label(score: float) -> str:
    if score > BULLISH_THRESHOLD:
        return "Bullish"
    if score < BEARISH_THRESHOLD:
        return "Bearish"
    return "Neutral"


def aggregate(per_headline: list[float]) -> dict:
    """Reduce per-headline scores ([-1,1]) to a readout dict.

    Returns: {score, label, confidence, article_count, insufficient}
      - score: mean * 100, range [-100, 100]
      - label: Bullish / Bearish / Neutral (Neutral when insufficient)
      - confidence: 0-100 from article count * directional agreement
      - insufficient: True when fewer than MIN_ARTICLES
    """
    count = len(per_headline)
    if count == 0:
        return {"score": 0.0, "label": "Neutral", "confidence": 0,
                "article_count": 0, "insufficient": True}

    mean = sum(per_headline) / count
    score = round(mean * 100, 1)

    # Agreement: of the headlines with a clear direction, the share that
    # matches the sign of the mean. All-flat -> 0 agreement.
    directional = [s for s in per_headline if s != 0]
    if directional and mean != 0:
        sign = 1 if mean > 0 else -1
        agreeing = sum(1 for s in directional if (s > 0) == (sign > 0))
        agreement = agreeing / len(directional)
    else:
        agreement = 0.0

    count_factor = min(count / CONFIDENCE_FULL_AT, 1.0)
    confidence = round(count_factor * agreement * 100)

    insufficient = count < MIN_ARTICLES
    if insufficient:
        confidence = min(confidence, INSUFFICIENT_CONFIDENCE_CAP)
        label = "Neutral"
    else:
        label = _label(score)

    return {"score": score, "label": label, "confidence": confidence,
            "article_count": count, "insufficient": insufficient}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sentiment_aggregate.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/aggregate_sentiment.py', doraise=True)"
git add tools/aggregate_sentiment.py tests/test_sentiment_aggregate.py
git commit -m "feat(sentiment): aggregation with confidence + thresholds"
```

---

## Task 4: Readout assembly — `build_readout`

Composes scoring + aggregation over already-fetched news items and attaches the headlines that drove the score. The router fetches items (Task 7/8) and passes them here.

**Files:**
- Modify: `tools/aggregate_sentiment.py`
- Test: `tests/test_sentiment_aggregate.py` (append)

- [ ] **Step 1: Write the failing test (append)**

Add to `tests/test_sentiment_aggregate.py`:

```python
from tools.aggregate_sentiment import build_readout


def _item(title, summary=""):
    return {"title": title, "summary": summary, "source": "Test",
            "url": "http://x", "published_at": "2026-06-14T10:00:00Z"}


def test_build_readout_shape_and_headlines():
    items = [
        _item("Record profit, beats estimates and raises guidance"),
        _item("Strong sales growth lifts shares to new high"),
        _item("Analysts upgrade with bullish outlook"),
    ]
    r = build_readout(items)
    assert set(r) == {"score", "label", "confidence", "article_count",
                      "insufficient", "top_headlines"}
    assert r["article_count"] == 3
    assert r["label"] == "Bullish"
    assert len(r["top_headlines"]) == 3
    h = r["top_headlines"][0]
    assert set(h) >= {"title", "source", "url", "published_at", "sentiment"}
    assert -1.0 <= h["sentiment"] <= 1.0


def test_build_readout_empty():
    r = build_readout([])
    assert r["article_count"] == 0
    assert r["insufficient"] is True
    assert r["top_headlines"] == []


def test_build_readout_caps_top_headlines():
    items = [_item(f"Profit beats estimates number {i}") for i in range(20)]
    r = build_readout(items, top_n=5)
    assert len(r["top_headlines"]) == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sentiment_aggregate.py -k build_readout -v`
Expected: FAIL — `ImportError: cannot import name 'build_readout'`

- [ ] **Step 3: Add the implementation (append to `tools/aggregate_sentiment.py`)**

```python
from tools.sentiment_engine import score_texts


def build_readout(items: list[dict], top_n: int = 6) -> dict:
    """Score a list of news items and assemble a readout for the API.

    `items` are dicts with keys: title, summary, source, url, published_at.
    Returns the aggregate() dict plus `top_headlines`: the strongest-signal
    headlines (largest |sentiment|), each annotated with its own score.
    """
    texts = [f"{it.get('title', '')}. {it.get('summary', '')}".strip()
             for it in items]
    scores = score_texts(texts)

    agg = aggregate(scores)

    ranked = sorted(
        zip(items, scores), key=lambda pair: abs(pair[1]), reverse=True
    )
    top_headlines = [
        {
            "title": it.get("title"),
            "source": it.get("source"),
            "url": it.get("url"),
            "published_at": it.get("published_at"),
            "sentiment": round(s, 3),
        }
        for it, s in ranked[:top_n]
    ]

    return {**agg, "top_headlines": top_headlines}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sentiment_aggregate.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/aggregate_sentiment.py', doraise=True)"
git add tools/aggregate_sentiment.py tests/test_sentiment_aggregate.py
git commit -m "feat(sentiment): build_readout assembles scored headlines"
```

---

## Task 5: News fetch — pure helpers (no network)

`tools/fetch_news.py` holds network functions AND pure helpers. We build/test the pure helpers first so the logic is covered without hitting RSS feeds.

**Files:**
- Create: `tools/fetch_news.py`
- Test: `tests/test_fetch_news.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fetch_news.py`:

```python
from tools.fetch_news import _normalize_entry, _dedupe, _matches_query, FEEDS


def test_feeds_have_both_scopes():
    assert "india" in FEEDS and "world" in FEEDS
    assert all(isinstance(u, str) and u.startswith("http") for u in FEEDS["india"])
    assert all(isinstance(u, str) and u.startswith("http") for u in FEEDS["world"])


def test_normalize_entry_maps_fields():
    raw = {
        "title": "  Reliance Q1 profit jumps  ",
        "summary": "<p>Net profit up 20%</p>",
        "link": "http://news/x",
        "published": "Sat, 14 Jun 2026 10:00:00 GMT",
    }
    item = _normalize_entry(raw, "Moneycontrol")
    assert item["title"] == "Reliance Q1 profit jumps"
    assert "<p>" not in item["summary"]
    assert item["url"] == "http://news/x"
    assert item["source"] == "Moneycontrol"
    assert item["published_at"]  # non-empty string


def test_normalize_entry_missing_fields_are_safe():
    item = _normalize_entry({}, "X")
    assert item["title"] == ""
    assert item["url"] == ""
    assert item["summary"] == ""


def test_dedupe_by_title_case_insensitive():
    items = [
        {"title": "Same Headline", "url": "a"},
        {"title": "same headline", "url": "b"},
        {"title": "Different", "url": "c"},
    ]
    out = _dedupe(items)
    assert len(out) == 2


def test_matches_query_on_title_and_summary():
    item = {"title": "Reliance Industries gains", "summary": "RIL up"}
    assert _matches_query(item, "Reliance")
    assert _matches_query(item, "reliance")
    assert not _matches_query(item, "Infosys")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fetch_news.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.fetch_news'`

- [ ] **Step 3: Write minimal implementation**

Create `tools/fetch_news.py`:

```python
"""Free news fetcher: RSS backbone + optional free-tier API enrichment.

No paid APIs. If NEWS_API_KEY is absent, the API path is skipped silently and
RSS alone is used. Network functions are thin wrappers around feedparser; the
parsing/normalisation logic lives in pure helpers so it is unit-testable.
"""
import os
import re

# Free RSS feeds. India = local market coverage; world = global context.
FEEDS: dict[str, list[str]] = {
    "india": [
        "https://www.moneycontrol.com/rss/marketreports.xml",
        "https://www.moneycontrol.com/rss/business.xml",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://www.business-standard.com/rss/markets-106.rss",
        "https://www.livemint.com/rss/markets",
    ],
    "world": [
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "http://feeds.reuters.com/reuters/businessNews",
    ],
}

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    return _TAG_RE.sub("", s or "").replace("&nbsp;", " ").strip()


def _normalize_entry(entry: dict, source: str) -> dict:
    """Map a feedparser entry (dict-like) to our normalized item shape."""
    return {
        "title": _strip_html(entry.get("title", "")),
        "summary": _strip_html(entry.get("summary", entry.get("description", ""))),
        "url": entry.get("link", "") or "",
        "source": source,
        "published_at": entry.get("published", entry.get("updated", "")) or "",
    }


def _dedupe(items: list[dict]) -> list[dict]:
    """Drop items with a duplicate title (case-insensitive), keep first seen."""
    seen: set[str] = set()
    out: list[dict] = []
    for it in items:
        key = (it.get("title") or "").strip().lower()
        if key and key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _matches_query(item: dict, query: str) -> bool:
    q = query.lower().strip()
    if not q:
        return False
    hay = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    return q in hay
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fetch_news.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/fetch_news.py', doraise=True)"
git add tools/fetch_news.py tests/test_fetch_news.py
git commit -m "feat(sentiment): news fetch pure helpers (normalize/dedupe/match)"
```

---

## Task 6: News fetch — network functions + graceful degradation

`fetch_feed_items(scope)` reads RSS via feedparser; `fetch_stock_news(query)` filters the pool and optionally enriches via a free-tier API. Both degrade gracefully (bad feed / missing key → skip, never raise). Tests monkeypatch `feedparser.parse` so no network is hit.

**Files:**
- Modify: `tools/fetch_news.py`
- Test: `tests/test_fetch_news.py` (append)

- [ ] **Step 1: Write the failing tests (append)**

```python
import tools.fetch_news as fn


class _FakeParsed:
    def __init__(self, entries):
        self.entries = entries
        self.bozo = 0


def test_fetch_feed_items_normalizes_and_dedupes(monkeypatch):
    def fake_parse(url):
        return _FakeParsed([
            {"title": "Dup", "link": "a", "summary": "x", "published": "now"},
            {"title": "dup", "link": "b", "summary": "y", "published": "now"},
            {"title": "Unique", "link": "c", "summary": "z", "published": "now"},
        ])
    monkeypatch.setattr(fn.feedparser, "parse", fake_parse)
    items = fn.fetch_feed_items("india", limit=10)
    titles = {i["title"] for i in items}
    assert "Unique" in titles
    assert len([i for i in items if i["title"].lower() == "dup"]) == 1
    assert all("source" in i for i in items)


def test_fetch_feed_items_skips_broken_feed(monkeypatch):
    def boom(url):
        raise RuntimeError("network down")
    monkeypatch.setattr(fn.feedparser, "parse", boom)
    # Must not raise; returns [] when every feed fails.
    assert fn.fetch_feed_items("india") == []


def test_fetch_stock_news_filters_pool(monkeypatch):
    def fake_parse(url):
        return _FakeParsed([
            {"title": "Reliance hits record", "link": "a", "summary": "", "published": "now"},
            {"title": "Infosys wins deal", "link": "b", "summary": "", "published": "now"},
        ])
    monkeypatch.setattr(fn.feedparser, "parse", fake_parse)
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    items = fn.fetch_stock_news("Reliance")
    assert items, "expected at least one matching item"
    assert all(_matches_query_safe(i, "Reliance") for i in items)


def _matches_query_safe(item, q):
    return q.lower() in f"{item['title']} {item['summary']}".lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fetch_news.py -k "feed or stock_news" -v`
Expected: FAIL — `AttributeError: module 'tools.fetch_news' has no attribute 'feedparser'` / missing functions

- [ ] **Step 3: Add the network functions (append to `tools/fetch_news.py`)**

```python
import feedparser  # noqa: E402  (kept after helpers for readability)

# Friendly source label per feed host.
_SOURCE_LABELS = {
    "moneycontrol": "Moneycontrol",
    "indiatimes": "Economic Times",
    "business-standard": "Business Standard",
    "livemint": "LiveMint",
    "dowjones": "MarketWatch",
    "cnbc": "CNBC",
    "reuters": "Reuters",
}


def _source_for(url: str) -> str:
    for needle, label in _SOURCE_LABELS.items():
        if needle in url:
            return label
    return "News"


def fetch_feed_items(scope: str, limit: int = 40) -> list[dict]:
    """Fetch + normalize + dedupe items for a scope ('india' | 'world').

    Never raises: a feed that errors or returns nothing is skipped.
    """
    items: list[dict] = []
    for url in FEEDS.get(scope, []):
        try:
            parsed = feedparser.parse(url)
            source = _source_for(url)
            for entry in getattr(parsed, "entries", []):
                items.append(_normalize_entry(entry, source))
        except Exception:
            continue  # graceful: skip this feed
    return _dedupe(items)[:limit]


def _fetch_api_news(query: str, limit: int) -> list[dict]:
    """Optional free-tier enrichment via GNews. No key -> []. Never raises."""
    key = os.getenv("NEWS_API_KEY")
    if not key:
        return []
    try:
        import requests
        resp = requests.get(
            "https://gnews.io/api/v4/search",
            params={"q": query, "lang": "en", "max": limit, "apikey": key},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        articles = resp.json().get("articles", [])
        return [{
            "title": _strip_html(a.get("title", "")),
            "summary": _strip_html(a.get("description", "")),
            "url": a.get("url", ""),
            "source": (a.get("source") or {}).get("name", "GNews"),
            "published_at": a.get("publishedAt", ""),
        } for a in articles]
    except Exception:
        return []


def fetch_stock_news(query: str, limit: int = 25) -> list[dict]:
    """News mentioning `query`: filter the RSS pool, then add free-tier API hits."""
    pool = fetch_feed_items("india", limit=80) + fetch_feed_items("world", limit=40)
    matched = [it for it in pool if _matches_query(it, query)]
    matched += _fetch_api_news(query, limit)
    return _dedupe(matched)[:limit]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fetch_news.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/fetch_news.py', doraise=True)"
git add tools/fetch_news.py tests/test_fetch_news.py
git commit -m "feat(sentiment): RSS fetch + optional API enrichment (graceful)"
```

---

## Task 7: Backend endpoint — `/sentiment/market`

Computes India + world readouts live (RSS → VADER → readout), cached. Mirrors the `cached()` + `clean_dict` + `verify_supabase_jwt` pattern from `backend/routers/analysis.py`.

**Files:**
- Create: `backend/routers/sentiment.py`
- Modify: `backend/main.py:15` (import) and `backend/main.py:109` (register)
- Test: `backend/tests/test_sentiment_router.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_sentiment_router.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
import main
from deps import verify_supabase_jwt

app = main.app
app.dependency_overrides[verify_supabase_jwt] = lambda: {"user_id": "test", "email": "t@t.dev"}
client = TestClient(app)


def test_market_endpoint_shape(monkeypatch):
    import tools.fetch_news as fn

    def fake_feed(scope, limit=40):
        return [
            {"title": "Markets rally on strong earnings", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
            {"title": "Index hits record high", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
            {"title": "Broad-based gains lift sentiment", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
        ]
    monkeypatch.setattr(fn, "fetch_feed_items", fake_feed)

    res = client.get("/api/v1/sentiment/market")
    assert res.status_code == 200
    body = res.json()
    assert set(body) >= {"india", "world", "as_of"}
    for scope in ("india", "world"):
        r = body[scope]
        assert set(r) >= {"score", "label", "confidence", "article_count", "top_headlines"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_sentiment_router.py -v`
Expected: FAIL — 404 (route not registered)

- [ ] **Step 3: Create the router**

Create `backend/routers/sentiment.py`:

```python
import sys
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from deps import verify_supabase_jwt
from services.cache import cached
from services.limiter import limiter
from services.logger import get_logger
from services.market_hours import adaptive_ttl
from services.serializers import clean_dict

log = get_logger(__name__)
router = APIRouter()

_TICKER = Query(..., pattern=r"^[A-Z0-9.\-&]{1,30}$", description="Ticker e.g. RELIANCE.NS")


def _scope_readout(scope: str) -> dict:
    from tools.fetch_news import fetch_feed_items
    from tools.aggregate_sentiment import build_readout
    return build_readout(fetch_feed_items(scope, limit=60))


@router.get("/sentiment/market")
@limiter.limit("20/minute")
async def get_market_sentiment(
    request: Request,
    user: dict = Depends(verify_supabase_jwt),
):
    """India + world market news sentiment (independent readouts)."""
    async def _compute():
        import asyncio
        india, world = await asyncio.gather(
            asyncio.to_thread(_scope_readout, "india"),
            asyncio.to_thread(_scope_readout, "world"),
        )
        return {"india": india, "world": world}

    try:
        data = await cached("sentiment:market", ttl=adaptive_ttl(1800), fn=_compute)
    except Exception as e:
        log.exception("Market sentiment failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Market sentiment failed: {e}")

    return {
        "india": clean_dict(data["india"]),
        "world": clean_dict(data["world"]),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
```

- [ ] **Step 4: Register the router in `backend/main.py`**

Change the import on line 15 from:

```python
from routers import health, market, analysis, options, payments
```
to:
```python
from routers import health, market, analysis, options, payments, sentiment
```

Add after line 109 (`app.include_router(payments.router, prefix="/api/v1")`):

```python
app.include_router(sentiment.router, prefix="/api/v1")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_sentiment_router.py -v`
Expected: PASS

- [ ] **Step 6: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('backend/routers/sentiment.py', doraise=True)"
git add backend/routers/sentiment.py backend/main.py backend/tests/test_sentiment_router.py
git commit -m "feat(sentiment): /sentiment/market endpoint"
```

---

## Task 8: Backend endpoint — `/sentiment/stock`

On-demand per-stock readout (VADER only in Phase 1) plus the two market labels as reference chips.

**Files:**
- Modify: `backend/routers/sentiment.py`
- Test: `backend/tests/test_sentiment_router.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
def test_stock_endpoint_shape(monkeypatch):
    import tools.fetch_news as fn

    def fake_stock_news(query, limit=25):
        return [
            {"title": f"{query} posts record profit", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
            {"title": f"{query} shares rally on upgrade", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
            {"title": f"Analysts bullish on {query}", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
        ]
    monkeypatch.setattr(fn, "fetch_stock_news", fake_stock_news)
    monkeypatch.setattr(fn, "fetch_feed_items", lambda scope, limit=40: [])

    res = client.get("/api/v1/sentiment/stock", params={"ticker": "RELIANCE.NS"})
    assert res.status_code == 200
    body = res.json()
    assert body["ticker"] == "RELIANCE.NS"
    assert set(body["sentiment"]) >= {"score", "label", "confidence", "top_headlines"}
    assert set(body["market"]) >= {"india_label", "world_label"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_sentiment_router.py::test_stock_endpoint_shape -v`
Expected: FAIL — 404

- [ ] **Step 3: Add the endpoint (append to `backend/routers/sentiment.py`)**

```python
@router.get("/sentiment/stock")
@limiter.limit("20/minute")
async def get_stock_sentiment(
    request: Request,
    ticker: str = _TICKER,
    user: dict = Depends(verify_supabase_jwt),
):
    """Per-stock news sentiment + India/world reference labels."""
    cache_key = f"sentiment:stock:{ticker}"

    def _compute():
        from tools.fetch_news import fetch_stock_news
        from tools.aggregate_sentiment import build_readout
        # Strip the exchange suffix for a cleaner news query (RELIANCE.NS -> RELIANCE).
        query = ticker.split(".")[0]
        stock = build_readout(fetch_stock_news(query))
        india = _scope_readout("india")
        world = _scope_readout("world")
        return {
            "sentiment": stock,
            "market": {"india_label": india["label"], "world_label": world["label"]},
        }

    try:
        data = await cached(cache_key, ttl=adaptive_ttl(3600), fn=_compute)
    except Exception as e:
        log.exception("Stock sentiment failed for %s: %s", ticker, e)
        raise HTTPException(status_code=503, detail=f"Stock sentiment failed: {e}")

    return {
        "ticker": ticker,
        "sentiment": clean_dict(data["sentiment"]),
        "market": data["market"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_sentiment_router.py -v`
Expected: both endpoint tests PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('backend/routers/sentiment.py', doraise=True)"
git add backend/routers/sentiment.py backend/tests/test_sentiment_router.py
git commit -m "feat(sentiment): /sentiment/stock endpoint"
```

---

## Task 9: Frontend — typed react-query hooks

Mirror `frontend/src/lib/api/analysis.ts` exactly (same `apiFetch`, `useQuery` shape).

**Files:**
- Create: `frontend/src/lib/api/sentiment.ts`

- [ ] **Step 1: Create the hook file**

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";

export interface Headline {
  title: string;
  source: string;
  url: string;
  published_at: string;
  sentiment: number; // -1..1
}

export interface SentimentReadout {
  score: number;        // -100..100
  label: "Bullish" | "Bearish" | "Neutral";
  confidence: number;   // 0..100
  article_count: number;
  insufficient: boolean;
  top_headlines: Headline[];
}

export interface MarketSentimentResponse {
  india: SentimentReadout;
  world: SentimentReadout;
  as_of: string;
}

export interface StockSentimentResponse {
  ticker: string;
  sentiment: SentimentReadout;
  market: { india_label: string; world_label: string };
}

export function useMarketSentiment() {
  return useQuery({
    queryKey: ["sentiment", "market"],
    queryFn: () => apiFetch<MarketSentimentResponse>("/api/v1/sentiment/market"),
    staleTime: 30 * 60 * 1000,
    retry: 2,
  });
}

export function useStockSentiment(ticker: string) {
  return useQuery({
    queryKey: ["sentiment", "stock", ticker],
    queryFn: () =>
      apiFetch<StockSentimentResponse>("/api/v1/sentiment/stock", { ticker }),
    staleTime: 60 * 60 * 1000,
    enabled: !!ticker,
  });
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors referencing `sentiment.ts`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api/sentiment.ts
git commit -m "feat(sentiment): frontend api hooks"
```

---

## Task 10: Frontend — page + components

> **READ FIRST (required):** `frontend/AGENTS.md` warns this Next.js differs from training data. Before writing any component, read the relevant guide under `frontend/node_modules/next/dist/docs/` and open an existing page (`frontend/src/app/dashboard/stocks/page.tsx`) and panel (`frontend/src/components/analysis/FundamentalsPanel.tsx`) to copy current conventions (client/server components, imports, styling tokens). Do **not** hand-write from memory.

**Files:**
- Create: `frontend/src/components/sentiment/SentimentGauge.tsx`
- Create: `frontend/src/components/sentiment/HeadlineList.tsx`
- Create: `frontend/src/app/dashboard/sentiment/page.tsx`

- [ ] **Step 1: `SentimentGauge.tsx`** — presentational card for one readout.

Props (exact): `{ title: string; readout: SentimentReadout }` (import `SentimentReadout` from `@/lib/api/sentiment`). Render: `title`, the `label` as a colored badge (Bullish=green, Bearish=red, Neutral=neutral — reuse the same color tokens `SignalCard.tsx`/`VerdictBanner.tsx` use for BUY/SELL/HOLD), the numeric `score` (−100…100), a confidence bar/percent, and `article_count`. When `readout.insufficient` is true, show an "Insufficient recent news" note instead of a confident call. Match the card container styling used in `FundamentalsPanel.tsx`.

- [ ] **Step 2: `HeadlineList.tsx`** — list of `Headline[]`.

Props (exact): `{ headlines: Headline[] }` (import `Headline` from `@/lib/api/sentiment`). Each row: title (linked to `url`, opens new tab), `source`, `published_at`, and a small sentiment chip colored by sign of `sentiment` (>0 green, <0 red, ~0 neutral). Empty array → render a muted "No headlines" line.

- [ ] **Step 3: `page.tsx`** — compose the page.

Behavior:
- Client component using `useMarketSentiment()` and `useStockSentiment(ticker)`.
- Top: two `SentimentGauge`s side by side (India, world) from `useMarketSentiment`, each with its `HeadlineList`. Show the `as_of` timestamp and a loading skeleton while pending (copy the loading pattern from `stocks/page.tsx`).
- Below: reuse the existing stock search component used on the stocks page (check `stocks/page.tsx` for the import) to pick a ticker; on select, render a `SentimentGauge` for `useStockSentiment(ticker).data.sentiment` plus small reference chips showing `market.india_label` and `market.world_label`, and its `HeadlineList`.
- Add the project disclaimer line (copy the wording/component used on `stocks/page.tsx` or `MethodologyNote.tsx`): sentiment bias, not investment advice.

- [ ] **Step 4: Type-check + build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: compiles; `/dashboard/sentiment` appears in the build route list.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/sentiment frontend/src/app/dashboard/sentiment
git commit -m "feat(sentiment): market + stock sentiment page"
```

---

## Task 11: Frontend — navigation entry

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx`
- Modify: `frontend/src/components/layout/MobileNav.tsx`

- [ ] **Step 1: Read both files** and find the array/list of nav links (look for the existing `Stocks` / `Scanner` entries).

- [ ] **Step 2: Add a "Sentiment" entry** mirroring an existing item exactly — same component, same icon import style (pick a fitting icon from the icon set already imported, e.g. a newspaper/activity icon), `href="/dashboard/sentiment"`, label `Sentiment`. Add it to both `Sidebar.tsx` and `MobileNav.tsx` in the same relative position (e.g. after Scanner).

- [ ] **Step 3: Type-check + build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/Sidebar.tsx frontend/src/components/layout/MobileNav.tsx
git commit -m "feat(sentiment): nav link to sentiment page"
```

---

## Task 12: Docs — README + workflow SOP

Per repo rule: update README on major additions; keep workflows current.

**Files:**
- Modify: `README.md`
- Create: `workflows/news_sentiment.md`

- [ ] **Step 1: Add a "News Sentiment" subsection to `README.md`**

Under Features, document: dedicated `/dashboard/sentiment` page; three independent readouts (stock / India / world, never blended); free RSS + VADER live (no paid APIs); endpoints `GET /api/v1/sentiment/market` and `GET /api/v1/sentiment/stock?ticker=`; optional `NEWS_API_KEY` for GNews enrichment; FinBERT nightly is Phase 2. Add `tools/fetch_news.py`, `tools/sentiment_engine.py`, `tools/aggregate_sentiment.py` to the Project Structure block.

- [ ] **Step 2: Create `workflows/news_sentiment.md`** — a short SOP:

Objective; inputs (scope or ticker); tools used (`fetch_news` → `sentiment_engine` → `aggregate_sentiment`); endpoints; how to test (`pytest tests/test_sentiment_aggregate.py tests/test_fetch_news.py`); edge cases (insufficient news, dead feed, missing API key); Phase 2 note (FinBERT nightly + Supabase `sentiment_snapshots`).

- [ ] **Step 3: Commit**

```bash
git add README.md workflows/news_sentiment.md
git commit -m "docs(sentiment): README + workflow SOP"
```

---

## Task 13: Final verification

- [ ] **Step 1: Run the full Python test suite**

Run: `python -m pytest tests/ -v && (cd backend && python -m pytest tests/ -v)`
Expected: all sentiment tests PASS. (Note: pre-existing AngelFallbackTest failures are a known baseline — see memory; do not treat as regressions, but confirm no NEW failures in sentiment files.)

- [ ] **Step 2: Frontend gates**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm run build`
Expected: no errors; `/dashboard/sentiment` route built.

- [ ] **Step 3: Manual smoke (optional but recommended)**

Start backend (`cd backend && uvicorn main:app --reload`) + frontend (`cd frontend && npm run dev`), log in with the guest test user (guest@localtest.dev / 12345678 — see memory), open `/dashboard/sentiment`, confirm India/world gauges populate and a stock search returns a readout.

- [ ] **Step 4: Final commit (if any docs/tweaks remain)**

```bash
git add -A
git commit -m "chore(sentiment): phase 1 verification"
```

---

## Out of Scope (Phase 2 — separate plan)
- FinBERT nightly scoring in the GitHub Actions EOD pipeline.
- Supabase `sentiment_snapshots` table + `tools/sentiment_store.py` + backend reading the store first.
- Trend-vs-yesterday deltas (needs stored history).
- Historical sentiment charts, alerts, feeding the composite signal.
