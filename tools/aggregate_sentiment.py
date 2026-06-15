"""Aggregate per-headline sentiment into one readout.

The SAME function is applied independently to each scope (stock / india /
world). Nothing is blended across scopes — that is a product decision in the
design spec, not an implementation detail to revisit here.
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from tools.sentiment_engine import score_headlines

_MIN_DT = datetime.min.replace(tzinfo=timezone.utc)


def _parse_published(s: str) -> datetime:
    """Parse a headline's published_at into a sortable, tz-aware datetime.

    Handles RFC-822 RSS dates ('Sat, 14 Jun 2026 ...') and ISO-8601; anything
    unparseable sorts to the bottom (oldest).
    """
    if not s:
        return _MIN_DT
    try:
        dt = parsedate_to_datetime(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return _MIN_DT

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


def build_readout(items: list[dict], top_n: int = 6, scorer=score_headlines) -> dict:
    """Score a list of news items and assemble a readout for the API.

    `items` are dicts with keys: title, summary, source, url, published_at.
    Returns the aggregate() dict plus `top_headlines`: the strongest-signal
    headlines (largest |sentiment|), each annotated with its own score.
    """
    texts = [f"{it.get('title', '')}. {it.get('summary', '')}".strip()
             for it in items]
    scores, scored_by = scorer(texts)

    agg = aggregate(scores)

    # Show the most RECENT headlines first (newest date at the top).
    ranked = sorted(
        zip(items, scores),
        key=lambda pair: _parse_published(pair[0].get("published_at")),
        reverse=True,
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

    return {**agg, "top_headlines": top_headlines, "scored_by": scored_by}
