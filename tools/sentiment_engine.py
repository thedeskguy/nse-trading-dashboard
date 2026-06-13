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
