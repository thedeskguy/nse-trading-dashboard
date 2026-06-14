import tools.sentiment_pipeline as sp


def test_targets_includes_market_and_stocks(monkeypatch):
    monkeypatch.setattr(sp, "NIFTY_50", ["RELIANCE", "TCS"])
    monkeypatch.setattr(sp, "get_stock_meta",
                        lambda t: {"name": t.title(), "sector": "Tech"})
    targets = sp.build_targets()
    scopes = {(t["scope"], t["key"]) for t in targets}
    assert ("market", "india") in scopes
    assert ("market", "world") in scopes
    assert ("stock", "RELIANCE") in scopes
    assert ("sector", "Tech") in scopes   # de-duplicated across stocks


def test_run_upserts_each_target(monkeypatch):
    monkeypatch.setattr(sp, "build_targets", lambda: [
        {"scope": "market", "key": "india", "fetch": lambda: [{"title": "t", "summary": "",
         "source": "x", "url": "u", "published_at": "now"}]},
    ])
    captured = []
    monkeypatch.setattr(sp, "upsert_snapshot",
                        lambda scope, key, readout, as_of: captured.append((scope, key, readout["scored_by"])))
    monkeypatch.setattr(sp, "_local_scorer", lambda texts: ([0.5] * len(texts), "finbert"))
    monkeypatch.setattr(sp.time, "sleep", lambda *a: None)
    sp.run(as_of_date="2026-06-14")
    assert captured == [("market", "india", "finbert")]
