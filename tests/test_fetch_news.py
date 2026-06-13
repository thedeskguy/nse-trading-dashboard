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
