import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from fastapi.testclient import TestClient
import main
from deps import verify_supabase_jwt

app = main.app


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[verify_supabase_jwt] = lambda: {"user_id": "test", "email": "t@t.dev"}
    yield
    app.dependency_overrides.pop(verify_supabase_jwt, None)


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
