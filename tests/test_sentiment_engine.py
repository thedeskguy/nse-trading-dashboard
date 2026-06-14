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
