from tools.fetch_news import _normalize_entry, _dedupe, _matches_query, FEEDS


def test_feeds_have_both_scopes():
    assert "india" in FEEDS and "world" in FEEDS
    assert all(isinstance(u, str) and u.startswith("http") for u in FEEDS["india"])
    assert all(isinstance(u, str) and u.startswith("http") for u in FEEDS["world"])


def test_normalize_entry_maps_fields():
    raw = {
        "title": "  Reliance Q1 profit jumps  ",
        "summary": "<p>Net profit up 20%</p>",
        "link": "http://news/x",
        "published": "Sat, 14 Jun 2026 10:00:00 GMT",
    }
    item = _normalize_entry(raw, "Moneycontrol")
    assert item["title"] == "Reliance Q1 profit jumps"
    assert "<p>" not in item["summary"]
    assert item["url"] == "http://news/x"
    assert item["source"] == "Moneycontrol"
    assert item["published_at"]  # non-empty string


def test_normalize_entry_missing_fields_are_safe():
    item = _normalize_entry({}, "X")
    assert item["title"] == ""
    assert item["url"] == ""
    assert item["summary"] == ""


def test_dedupe_by_title_case_insensitive():
    items = [
        {"title": "Same Headline", "url": "a"},
        {"title": "same headline", "url": "b"},
        {"title": "Different", "url": "c"},
    ]
    out = _dedupe(items)
    assert len(out) == 2


def test_matches_query_on_title_and_summary():
    item = {"title": "Reliance Industries gains", "summary": "RIL up"}
    assert _matches_query(item, "Reliance")
    assert _matches_query(item, "reliance")
    assert not _matches_query(item, "Infosys")


import tools.fetch_news as fn


class _FakeParsed:
    def __init__(self, entries):
        self.entries = entries
        self.bozo = 0


def test_fetch_feed_items_normalizes_and_dedupes(monkeypatch):
    def fake_parse(url):
        return _FakeParsed([
            {"title": "Dup", "link": "a", "summary": "x", "published": "now"},
            {"title": "dup", "link": "b", "summary": "y", "published": "now"},
            {"title": "Unique", "link": "c", "summary": "z", "published": "now"},
        ])
    monkeypatch.setattr(fn.feedparser, "parse", fake_parse)
    items = fn.fetch_feed_items("india", limit=10)
    titles = {i["title"] for i in items}
    assert "Unique" in titles
    assert len([i for i in items if i["title"].lower() == "dup"]) == 1
    assert all("source" in i for i in items)


def test_fetch_feed_items_skips_broken_feed(monkeypatch):
    def boom(url):
        raise RuntimeError("network down")
    monkeypatch.setattr(fn.feedparser, "parse", boom)
    # Must not raise; returns [] when every feed fails.
    assert fn.fetch_feed_items("india") == []


def test_fetch_stock_news_filters_pool(monkeypatch):
    def fake_parse(url):
        return _FakeParsed([
            {"title": "Reliance hits record", "link": "a", "summary": "", "published": "now"},
            {"title": "Infosys wins deal", "link": "b", "summary": "", "published": "now"},
        ])
    monkeypatch.setattr(fn.feedparser, "parse", fake_parse)
    # Isolate the pool-filter path: Google News is the primary per-stock source
    # and is exercised separately below.
    monkeypatch.setattr(fn, "_fetch_google_news", lambda q, limit=40, recency_days=None: [])
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    items = fn.fetch_stock_news("Reliance")
    assert items, "expected at least one matching item"
    assert all(_matches_query_safe(i, "Reliance") for i in items)


def _matches_query_safe(item, q):
    return q.lower() in f"{item['title']} {item['summary']}".lower()


def test_strip_html_unescapes_entities():
    assert fn._strip_html("AT&amp;T says it&#39;s &nbsp;up") == "AT&T says it's  up"
    assert fn._strip_html("<b>F&amp;O</b> Talk") == "F&O Talk"


def test_fetch_google_news_normalizes(monkeypatch):
    def fake_parse(url):
        assert "news.google.com/rss/search" in url
        return _FakeParsed([
            {"title": "Reliance shares rally - ET", "link": "g1",
             "summary": "", "published": "now", "source": {"title": "ET"}},
            {"title": "Reliance Q1 beats - Mint", "link": "g2",
             "summary": "", "published": "now"},
        ])
    monkeypatch.setattr(fn.feedparser, "parse", fake_parse)
    items = fn._fetch_google_news("RELIANCE share price NSE")
    assert len(items) == 2
    assert items[0]["source"] == "ET"          # from <source> tag
    assert items[1]["source"] == "Google News"  # fallback when no source tag


def test_fetch_google_news_never_raises(monkeypatch):
    def boom(url):
        raise RuntimeError("network down")
    monkeypatch.setattr(fn.feedparser, "parse", boom)
    assert fn._fetch_google_news("X") == []


def test_fetch_stock_news_includes_google(monkeypatch):
    google_items = [
        {"title": "RELIANCE jumps on upgrade", "summary": "", "source": "ET",
         "url": "g", "published_at": "now"},
    ]
    monkeypatch.setattr(fn, "_fetch_google_news", lambda q, limit=40, recency_days=None: google_items)
    monkeypatch.setattr(fn, "fetch_feed_items", lambda scope, limit=40: [])
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    items = fn.fetch_stock_news("RELIANCE")
    assert any(i["title"] == "RELIANCE jumps on upgrade" for i in items)


def test_fetch_stock_news_uses_company_name(monkeypatch):
    seen = {}

    def fake_google(query, limit=40, recency_days=None):
        seen["q"] = query
        seen["days"] = recency_days
        return []
    monkeypatch.setattr(fn, "_fetch_google_news", fake_google)
    monkeypatch.setattr(fn, "fetch_feed_items", lambda scope, limit=40: [])
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    fn.fetch_stock_news("RAJESHEXPO", name="Rajesh Exports")
    assert "Rajesh Exports" in seen["q"]      # name, not the symbol
    assert seen["days"] == fn.STOCK_NEWS_DAYS  # recency-restricted


def test_fetch_google_news_applies_recency(monkeypatch):
    seen = {}

    def fake_parse(url):
        seen["url"] = url
        return _FakeParsed([])
    monkeypatch.setattr(fn.feedparser, "parse", fake_parse)
    fn._fetch_google_news("Reliance stock", recency_days=30)
    assert "when%3A30d" in seen["url"] or "when:30d" in seen["url"]


def test_fetch_sector_news_empty_sector_returns_empty():
    assert fn.fetch_sector_news("") == []
    assert fn.fetch_sector_news(None) == []


def test_fetch_sector_news_queries_google(monkeypatch):
    seen = {}

    def fake_google(query, limit=25, recency_days=None):
        seen["q"] = query
        seen["days"] = recency_days
        return [{"title": "Energy stocks rally", "summary": "", "source": "ET",
                 "url": "e", "published_at": "now"}]
    monkeypatch.setattr(fn, "_fetch_google_news", fake_google)
    items = fn.fetch_sector_news("Energy")
    assert items and items[0]["title"] == "Energy stocks rally"
    assert "Energy" in seen["q"] and "sector" in seen["q"].lower()
    assert seen["days"] == fn.SECTOR_NEWS_DAYS
