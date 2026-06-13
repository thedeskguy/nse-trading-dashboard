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
