"""Local FinBERT scoring (transformers + torch). CI / nightly-job use only.

NEVER imported by the FastAPI backend — torch is too heavy for the free
Render instance. The on-demand backend path uses the HF API or VADER instead.
Mapping matches the HF path: P(positive) - P(negative) in [-1, 1].
"""

_pipe = None


def _get_pipe():
    """Lazily build and cache the FinBERT text-classification pipeline."""
    global _pipe
    if _pipe is None:
        from transformers import pipeline
        _pipe = pipeline(
            "text-classification", model="ProsusAI/finbert", top_k=None
        )
    return _pipe


def score_texts_finbert_local(texts: list[str]) -> list[float]:
    """Score each text in [-1, 1] with a locally-run FinBERT model.

    Blank/empty strings score 0.0 without invoking the model (order preserved).
    """
    out = [0.0] * len(texts)
    idx = [i for i, t in enumerate(texts) if t and t.strip()]
    payload = [texts[i] for i in idx]
    if not payload:
        return out

    results = _get_pipe()(payload, truncation=True)
    for j, preds in enumerate(results):
        ls = {p["label"].lower(): float(p["score"]) for p in preds}
        signed = ls.get("positive", 0.0) - ls.get("negative", 0.0)
        out[idx[j]] = max(-1.0, min(1.0, round(signed, 4)))
    return out
