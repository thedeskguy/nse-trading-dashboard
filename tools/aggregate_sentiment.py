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
