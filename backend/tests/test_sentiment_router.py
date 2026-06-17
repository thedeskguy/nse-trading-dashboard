import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from fastapi.testclient import TestClient
import main
from deps import verify_supabase_jwt

app = main.app
client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[verify_supabase_jwt] = lambda: {"user_id": "test", "email": "t@t.dev"}
    yield
    app.dependency_overrides.pop(verify_supabase_jwt, None)


@pytest.fixture(autouse=True)
def _clear_cache():
    # The endpoints cache results in-process; clear between tests so a cached
    # result from one test does not leak into another (e.g. snapshot vs compute).
    from services.cache import _store
    _store.clear()
    yield


def test_market_endpoint_shape(monkeypatch):
    import tools.fetch_news as fn

    def fake_feed(scope, limit=40):
        return [
            {"title": "Markets rally on strong earnings", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
            {"title": "Index hits record high", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
            {"title": "Broad-based gains lift sentiment", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
        ]
    monkeypatch.setattr(fn, "fetch_feed_items", fake_feed)

    client = TestClient(app)
    res = client.get("/api/v1/sentiment/market")
    assert res.status_code == 200
    body = res.json()
    assert set(body) >= {"india", "world", "as_of"}
    for scope in ("india", "world"):
        r = body[scope]
        assert set(r) >= {"score", "label", "confidence", "article_count", "top_headlines"}


def test_stock_endpoint_shape(monkeypatch):
    import tools.fetch_news as fn

    def fake_stock_news(query, name=None, limit=25):
        return [
            {"title": f"{query} posts record profit", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
            {"title": f"{query} shares rally on upgrade", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
            {"title": f"Analysts bullish on {query}", "summary": "",
             "source": "Test", "url": "u", "published_at": "now"},
        ]
    import tools.fetch_fundamentals as ff
    monkeypatch.setattr(fn, "fetch_stock_news", fake_stock_news)
    monkeypatch.setattr(fn, "fetch_feed_items", lambda scope, limit=40: [])
    monkeypatch.setattr(ff, "get_stock_meta", lambda t: {"name": "Reliance", "sector": "Energy"})
    monkeypatch.setattr(fn, "fetch_sector_news", lambda sector, limit=25: [
        {"title": f"{sector} stocks rally", "summary": "", "source": "ET",
         "url": "s1", "published_at": "now"},
        {"title": f"{sector} sector outlook strong", "summary": "", "source": "Mint",
         "url": "s2", "published_at": "now"},
        {"title": f"{sector} demand rises sharply", "summary": "", "source": "BS",
         "url": "s3", "published_at": "now"},
    ])

    res = client.get("/api/v1/sentiment/stock", params={"ticker": "RELIANCE.NS"})
    assert res.status_code == 200
    body = res.json()
    assert body["ticker"] == "RELIANCE.NS"
    assert set(body["sentiment"]) >= {"score", "label", "confidence", "top_headlines"}
    assert set(body["market"]) >= {"india_label", "world_label"}
    assert body["sector"] == "Energy"
    assert set(body["industry"]) >= {"score", "label", "confidence", "top_headlines"}


def test_stock_endpoint_industry_null_when_sector_unknown(monkeypatch):
    import tools.fetch_news as fn
    import tools.fetch_fundamentals as ff
    monkeypatch.setattr(fn, "fetch_stock_news", lambda q, name=None, limit=25: [])
    monkeypatch.setattr(fn, "fetch_feed_items", lambda scope, limit=40: [])
    monkeypatch.setattr(ff, "get_stock_meta", lambda t: {"name": None, "sector": None})

    res = client.get("/api/v1/sentiment/stock", params={"ticker": "UNKNOWN.NS"})
    assert res.status_code == 200
    body = res.json()
    assert body["sector"] is None
    assert body["industry"] is None


def test_market_endpoint_uses_snapshot(monkeypatch):
    import tools.sentiment_store as ss

    def fake_snapshot(scope, key):
        return {"score": 55.0, "label": "Bullish", "confidence": 90,
                "article_count": 60, "insufficient": False,
                "top_headlines": [], "scored_by": "finbert"}
    monkeypatch.setattr(ss, "get_snapshot", fake_snapshot)

    res = client.get("/api/v1/sentiment/market")
    assert res.status_code == 200
    body = res.json()
    assert body["india"]["scored_by"] == "finbert"
    assert body["india"]["label"] == "Bullish"
