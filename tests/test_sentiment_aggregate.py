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
