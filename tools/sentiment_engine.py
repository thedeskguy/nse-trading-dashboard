"""Free, local sentiment scoring.

Phase 1: VADER lexicon scoring only (instant, no model download, no API).
FinBERT (nightly, heavy) is added in Phase 2 behind the same module.
"""
import os

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_FINBERT_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"

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
