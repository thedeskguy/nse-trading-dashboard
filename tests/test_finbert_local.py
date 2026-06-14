import tools.finbert_local as fl
from tools.finbert_local import score_texts_finbert_local


def _preds(pos, neg, neu):
    return [
        {"label": "positive", "score": pos},
        {"label": "negative", "score": neg},
        {"label": "neutral", "score": neu},
    ]


def test_local_finbert_maps_pos_minus_neg(monkeypatch):
    # Fake the transformers pipeline: returns a list (per input) of label dicts.
    def fake_pipe(texts, truncation=True):
        return [_preds(0.8, 0.1, 0.1), _preds(0.1, 0.8, 0.1)]
    monkeypatch.setattr(fl, "_get_pipe", lambda: fake_pipe)

    scores = score_texts_finbert_local(["up", "down"])
    assert round(scores[0], 1) == 0.7
    assert round(scores[1], 1) == -0.7


def test_local_finbert_blanks_score_zero(monkeypatch):
    def fake_pipe(texts, truncation=True):
        assert texts == ["real"]
        return [_preds(0.5, 0.3, 0.2)]
    monkeypatch.setattr(fl, "_get_pipe", lambda: fake_pipe)

    scores = score_texts_finbert_local(["", "real", "  "])
    assert scores[0] == 0.0 and scores[2] == 0.0
    assert round(scores[1], 1) == 0.2


def test_local_finbert_empty_input(monkeypatch):
    monkeypatch.setattr(fl, "_get_pipe", lambda: (_ for _ in ()).throw(
        AssertionError("pipe must not be built for empty input")))
    assert score_texts_finbert_local([]) == []
