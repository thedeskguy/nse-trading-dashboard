# News Sentiment Phase 2a — On-Demand FinBERT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score per-stock / sector / market headlines with FinBERT via the free Hugging Face Inference API when an `HF_TOKEN` is set, falling back to VADER otherwise — closing the on-demand quality gap (a scam-hit stock should read bearish) with no CI or Supabase work.

**Architecture:** Add a FinBERT HF-API scorer and a `score_headlines` selector to `tools/sentiment_engine.py`; `build_readout` calls the selector and records which scorer was used (`scored_by`). Everything downstream — `aggregate()`, the API shape, the UI — is unchanged except a small "scored by" chip. The Render backend stays free/light: only an HTTP call, no torch.

**Tech Stack:** Python 3 · `requests` (already a dep) · Hugging Face Inference API (`ProsusAI/finbert`) · pytest · Next.js / TypeScript.

**Reference spec:** `docs/superpowers/specs/2026-06-14-news-sentiment-phase2-finbert-design.md` (§3, §4, §5.1, §6, §7, §8 "Phase 2a")

---

## File Structure

**Modify:**
- `tools/sentiment_engine.py` — add `FinbertUnavailable`, `score_texts_finbert_api`, `score_headlines`. Keep `score_texts` (VADER) as-is.
- `tools/aggregate_sentiment.py` — `build_readout` uses `score_headlines`, returns `scored_by`.
- `tests/test_sentiment_aggregate.py` — update the `build_readout` shape test for the new `scored_by` key.
- `frontend/src/lib/api/sentiment.ts` — add `scored_by` to `SentimentReadout`.
- `frontend/src/components/sentiment/SentimentGauge.tsx` — render a small "scored by" chip.
- `backend/.env.example` and `.env.example` — document `HF_TOKEN`.
- `README.md`, `workflows/news_sentiment.md` — note FinBERT-on-demand + `HF_TOKEN`.

**Create:**
- `tests/test_sentiment_engine.py` — FinBERT-API + selector tests (network mocked).

**Naming note:** the readout's scorer field is `scored_by` (`"finbert"` | `"vader"`), NOT `source`, because each headline already has a `source` (its publisher). This is a deliberate clarity improvement over the spec's `source` wording.

---

## Task 1: Verify the HF Inference API works for FinBERT (spike)

This confirms the external dependency before building against it. No code commit — it produces a go/no-go finding. If it fails, the rest of the plan still ships safely (everything degrades to VADER, i.e. today's behaviour), and FinBERT quality arrives via Phase 2b's nightly torch path instead.

**Prereq:** a free Hugging Face token (https://huggingface.co/settings/tokens, "Read" scope).

- [ ] **Step 1: Run the verification script with a token**

```bash
HF_TOKEN=hf_xxx python3 - <<'PY'
import os, requests, json
tok = os.environ["HF_TOKEN"]
r = requests.post(
    "https://api-inference.huggingface.co/models/ProsusAI/finbert",
    headers={"Authorization": f"Bearer {tok}"},
    json={"inputs": [
        "Rajesh Exports shares hit 5% lower circuit as firm disputes SEBI allegations",
        "Company posts record profit, beats estimates and raises guidance",
    ], "options": {"wait_for_model": True}},
    timeout=30,
)
print("status:", r.status_code)
print(json.dumps(r.json(), indent=2)[:800])
PY
```

Expected: `status: 200` and a list of two results, each a list of
`{"label": "positive|negative|neutral", "score": ...}`. The first (bearish)
should have the highest score on `negative`; the second on `positive`.

- [ ] **Step 2: Record the finding**

- If 200 with the expected shape → proceed; the implementation below matches it.
- If 503 "model loading" → re-run once (the `wait_for_model` option should handle it); if it persists, note it — the code treats it as `FinbertUnavailable` → VADER fallback.
- If 401/403/404 or the endpoint is gone → **stop and report to the controller**: the HF serverless path is unavailable; we ship Phase 2a as VADER-only (no regression) and rely on Phase 2b. Do not fabricate a passing result.

---

## Task 2: FinBERT HF-API scorer

**Files:**
- Modify: `tools/sentiment_engine.py`
- Test: `tests/test_sentiment_engine.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sentiment_engine.py`:

```python
import pytest
import tools.sentiment_engine as se
from tools.sentiment_engine import score_texts_finbert_api, FinbertUnavailable


class _FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def _finbert_preds(pos, neg, neu):
    return [
        {"label": "positive", "score": pos},
        {"label": "negative", "score": neg},
        {"label": "neutral", "score": neu},
    ]


def test_finbert_maps_pos_minus_neg(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")

    def fake_post(url, headers=None, json=None, timeout=None):
        # one result list per input
        return _FakeResp(200, [
            _finbert_preds(0.8, 0.1, 0.1),   # bullish -> +0.7
            _finbert_preds(0.1, 0.8, 0.1),   # bearish -> -0.7
        ])
    monkeypatch.setattr(se.requests, "post", fake_post)

    scores = score_texts_finbert_api(["up news", "down news"])
    assert len(scores) == 2
    assert round(scores[0], 1) == 0.7
    assert round(scores[1], 1) == -0.7
    assert all(-1.0 <= s <= 1.0 for s in scores)


def test_finbert_blank_inputs_score_zero_without_call(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")

    def fake_post(url, headers=None, json=None, timeout=None):
        # only the single non-blank input should be sent
        assert json["inputs"] == ["real headline"]
        return _FakeResp(200, [_finbert_preds(0.6, 0.2, 0.2)])
    monkeypatch.setattr(se.requests, "post", fake_post)

    scores = score_texts_finbert_api(["", "real headline", "   "])
    assert scores[0] == 0.0 and scores[2] == 0.0
    assert round(scores[1], 1) == 0.4


def test_finbert_no_token_raises(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(FinbertUnavailable):
        score_texts_finbert_api(["x"])


def test_finbert_non_200_raises(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    monkeypatch.setattr(se.requests, "post",
                        lambda *a, **k: _FakeResp(503, {"error": "loading"}))
    with pytest.raises(FinbertUnavailable):
        score_texts_finbert_api(["x"])


def test_finbert_network_error_raises(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")

    def boom(*a, **k):
        raise RuntimeError("timeout")
    monkeypatch.setattr(se.requests, "post", boom)
    with pytest.raises(FinbertUnavailable):
        score_texts_finbert_api(["x"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sentiment_engine.py -v`
Expected: FAIL — `ImportError: cannot import name 'score_texts_finbert_api'`

- [ ] **Step 3: Implement (append to `tools/sentiment_engine.py`)**

First, change the module imports at the top from:
```python
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
```
to:
```python
import os

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_FINBERT_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
```

Then append at the end of the file:
```python
class FinbertUnavailable(Exception):
    """Raised when FinBERT scoring via the HF Inference API cannot complete."""


def score_texts_finbert_api(texts: list[str]) -> list[float]:
    """Score each text in [-1, 1] via the Hugging Face Inference API (FinBERT).

    Mapping: P(positive) - P(negative). Blank/empty strings score 0.0 without
    an API call (order preserved). Raises FinbertUnavailable on any failure
    (no token, non-200, network error) so the caller can fall back to VADER.
    """
    token = os.getenv("HF_TOKEN")
    if not token:
        raise FinbertUnavailable("HF_TOKEN not set")

    out = [0.0] * len(texts)
    idx_nonblank = [i for i, t in enumerate(texts) if t and t.strip()]
    payload_texts = [texts[i] for i in idx_nonblank]
    if not payload_texts:
        return out

    try:
        resp = requests.post(
            _FINBERT_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": payload_texts, "options": {"wait_for_model": True}},
            timeout=20,
        )
    except Exception as e:
        raise FinbertUnavailable(f"request failed: {e}")

    if resp.status_code != 200:
        raise FinbertUnavailable(f"HF {resp.status_code}: {resp.text[:120]}")

    try:
        data = resp.json()
        # Normalise: a single-input response may be one list of preds, not nested.
        if data and isinstance(data[0], dict):
            data = [data]
        for j, preds in enumerate(data):
            label_scores = {p["label"].lower(): float(p["score"]) for p in preds}
            signed = label_scores.get("positive", 0.0) - label_scores.get("negative", 0.0)
            out[idx_nonblank[j]] = max(-1.0, min(1.0, round(signed, 4)))
    except Exception as e:
        raise FinbertUnavailable(f"bad response: {e}")

    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sentiment_engine.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/sentiment_engine.py', doraise=True)"
git add tools/sentiment_engine.py tests/test_sentiment_engine.py
git commit -m "feat(sentiment): FinBERT scorer via Hugging Face Inference API"
```

---

## Task 3: `score_headlines` selector (FinBERT → VADER)

**Files:**
- Modify: `tools/sentiment_engine.py`
- Test: `tests/test_sentiment_engine.py` (append)

- [ ] **Step 1: Append the failing tests**

```python
from tools.sentiment_engine import score_headlines


def test_selector_uses_vader_without_token(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    scores, source = score_headlines(["Company beats estimates, profit jumps"])
    assert source == "vader"
    assert len(scores) == 1


def test_selector_uses_finbert_with_token(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    monkeypatch.setattr(se, "score_texts_finbert_api", lambda texts: [0.5] * len(texts))
    scores, source = score_headlines(["x", "y"])
    assert source == "finbert"
    assert scores == [0.5, 0.5]


def test_selector_falls_back_to_vader_on_finbert_failure(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")

    def boom(texts):
        raise FinbertUnavailable("rate limited")
    monkeypatch.setattr(se, "score_texts_finbert_api", boom)
    scores, source = score_headlines(["Company crashes, shares plunge"])
    assert source == "vader"
    assert len(scores) == 1


def test_selector_empty_texts(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    scores, source = score_headlines([])
    assert scores == []
    assert source == "vader"   # nothing to score -> no API call
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sentiment_engine.py -k selector -v`
Expected: FAIL — `ImportError: cannot import name 'score_headlines'`

- [ ] **Step 3: Implement (append to `tools/sentiment_engine.py`)**

```python
def score_headlines(texts: list[str]) -> tuple[list[float], str]:
    """Return (per-headline scores in [-1,1], scorer name).

    Prefers FinBERT via the HF API when HF_TOKEN is set and there is text to
    score; otherwise, or on any FinBERT failure, uses VADER. The scorer name
    ('finbert' | 'vader') is surfaced to the UI for transparency.
    """
    if texts and os.getenv("HF_TOKEN"):
        try:
            return score_texts_finbert_api(texts), "finbert"
        except FinbertUnavailable:
            pass
    return score_texts(texts), "vader"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sentiment_engine.py -v`
Expected: all PASS

- [ ] **Step 5: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/sentiment_engine.py', doraise=True)"
git add tools/sentiment_engine.py tests/test_sentiment_engine.py
git commit -m "feat(sentiment): scorer selector with VADER fallback"
```

---

## Task 4: `build_readout` records the scorer

**Files:**
- Modify: `tools/aggregate_sentiment.py`
- Test: `tests/test_sentiment_aggregate.py`

- [ ] **Step 1: Update the existing shape test (it asserts an exact key set)**

In `tests/test_sentiment_aggregate.py`, find `test_build_readout_shape_and_headlines` and change the key-set assertion from:
```python
    assert set(r) == {"score", "label", "confidence", "article_count",
                      "insufficient", "top_headlines"}
```
to:
```python
    assert set(r) == {"score", "label", "confidence", "article_count",
                      "insufficient", "top_headlines", "scored_by"}
    assert r["scored_by"] in ("finbert", "vader")
```

- [ ] **Step 2: Add a fallback-source test (append to the same file)**

```python
def test_build_readout_scored_by_vader_without_token(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    r = build_readout([_item("Profit beats estimates and raises guidance")])
    assert r["scored_by"] == "vader"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_sentiment_aggregate.py -k build_readout -v`
Expected: FAIL — `KeyError: 'scored_by'` / missing key in the set assertion

- [ ] **Step 4: Implement the change in `tools/aggregate_sentiment.py`**

Change the import at the top from:
```python
from tools.sentiment_engine import score_texts
```
to:
```python
from tools.sentiment_engine import score_headlines
```

In `build_readout`, change:
```python
    scores = score_texts(texts)

    agg = aggregate(scores)
```
to:
```python
    scores, scored_by = score_headlines(texts)

    agg = aggregate(scores)
```

And change the return from:
```python
    return {**agg, "top_headlines": top_headlines}
```
to:
```python
    return {**agg, "top_headlines": top_headlines, "scored_by": scored_by}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_sentiment_aggregate.py -v`
Expected: all PASS

- [ ] **Step 6: Confirm the backend router tests still pass (they use `>=`, so `scored_by` is additive)**

Run: `cd backend && python -m pytest tests/test_sentiment_router.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Syntax check + commit**

```bash
python -c "import py_compile; py_compile.compile('tools/aggregate_sentiment.py', doraise=True)"
git add tools/aggregate_sentiment.py tests/test_sentiment_aggregate.py
git commit -m "feat(sentiment): build_readout reports scorer (scored_by)"
```

---

## Task 5: Config + docs for `HF_TOKEN`

**Files:**
- Modify: `backend/.env.example`, `.env.example` (whichever exist)
- Modify: `README.md`, `workflows/news_sentiment.md`

- [ ] **Step 1: Add `HF_TOKEN` to the env examples**

Append to `backend/.env.example` (and root `.env.example` if present):
```
# Optional: free Hugging Face token enables FinBERT scoring (finance-trained).
# Absent -> sentiment falls back to VADER. https://huggingface.co/settings/tokens
HF_TOKEN=
```

- [ ] **Step 2: Update the README "News Sentiment" subsection**

Add a sentence to the scoring-engine line: with `HF_TOKEN` set, per-headline scoring uses **FinBERT** (`ProsusAI/finbert`) via the free Hugging Face Inference API — finance-trained, so "lower circuit" / "misses estimates" read correctly; without it (or on rate-limit), it falls back to VADER. Each readout reports `scored_by` (`finbert` | `vader`).

- [ ] **Step 3: Update `workflows/news_sentiment.md`**

In the tool sequence, note that `sentiment_engine.score_headlines()` prefers FinBERT via the HF API when `HF_TOKEN` is set and falls back to VADER; add `HF_TOKEN` (optional) to the config table.

- [ ] **Step 4: Commit**

```bash
git add backend/.env.example .env.example README.md workflows/news_sentiment.md
git commit -m "docs(sentiment): document HF_TOKEN / FinBERT on-demand scoring"
```

---

## Task 6: Frontend — show the scorer

> **READ FIRST:** `frontend/AGENTS.md` warns this Next.js differs from training data. Mirror the existing `SentimentGauge.tsx` styling/tokens; do not hand-write speculative APIs.

**Files:**
- Modify: `frontend/src/lib/api/sentiment.ts`
- Modify: `frontend/src/components/sentiment/SentimentGauge.tsx`

- [ ] **Step 1: Add `scored_by` to the type**

In `frontend/src/lib/api/sentiment.ts`, add to the `SentimentReadout` interface:
```typescript
  scored_by?: "finbert" | "vader";
```

- [ ] **Step 2: Render a small scorer chip in `SentimentGauge.tsx`**

In the gauge header (next to the `title`, where the label badge already renders), add a small muted chip showing the scorer when present — e.g. uppercase `FinBERT` / `VADER` in a `text-[10px]` muted pill, mirroring the existing badge/chip classes already used in the file. Keep it unobtrusive (it's a provenance hint, not a headline). Use `readout.scored_by` and render nothing when it is undefined.

- [ ] **Step 3: Type-check + build**

Run: `cd frontend && npx tsc --noEmit && npx next build --webpack`
Expected: tsc clean; build compiles; `/dashboard/sentiment` route present. (Local default `npm run build` uses Turbopack, which fails on darwin/arm64 — use `--webpack` locally; CI on Linux is fine.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api/sentiment.ts frontend/src/components/sentiment/SentimentGauge.tsx
git commit -m "feat(sentiment): show scorer (FinBERT/VADER) on each gauge"
```

---

## Task 7: Final verification

- [ ] **Step 1: Full Python suites**

Run: `python -m pytest tests/test_sentiment_engine.py tests/test_sentiment_aggregate.py tests/test_fetch_news.py -v && (cd backend && python -m pytest tests/test_sentiment_router.py -v)`
Expected: all sentiment tests PASS.

- [ ] **Step 2: Frontend gates**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: clean.

- [ ] **Step 3: Live end-to-end (only if Task 1 verified HF works)**

Start the backend with the token and confirm a long-tail, bad-news stock now reads via FinBERT:
```bash
cd backend && SUPABASE_URL="" ALLOW_UNVERIFIED_JWT=1 HF_TOKEN=hf_xxx \
  python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
# then, with a dev bearer token, GET /api/v1/sentiment/stock?ticker=RAJESHEXPO.NS
# expect: sentiment.scored_by == "finbert" and a more clearly bearish score than VADER gave.
```
Record the before/after (VADER vs FinBERT) score for RAJESHEXPO. If HF was not verified in Task 1, skip this step — the suite + VADER fallback guarantee no regression.

- [ ] **Step 4: Final commit (if any docs/tweaks remain)**

```bash
git add -A && git commit -m "chore(sentiment): phase 2a verification"
```

---

## Out of Scope (Phase 2b — separate plan)
- Local FinBERT (`transformers`/`torch`) in the nightly CI job.
- `tools/sentiment_store.py` + Supabase `sentiment_snapshots` table.
- Backend reading the nightly store first (market + Nifty 50 coverage).
- Trend-vs-yesterday deltas.
