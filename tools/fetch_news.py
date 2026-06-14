"""Free news fetcher: RSS backbone + optional free-tier API enrichment.

No paid APIs. If NEWS_API_KEY is absent, the API path is skipped silently and
RSS alone is used. Network functions are thin wrappers around feedparser; the
parsing/normalisation logic lives in pure helpers so it is unit-testable.
"""
import html
import os
import re

import feedparser

# Free RSS feeds. India = local market coverage; world = global context.
FEEDS: dict[str, list[str]] = {
    "india": [
        "https://www.moneycontrol.com/rss/marketreports.xml",
        "https://www.moneycontrol.com/rss/business.xml",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://www.business-standard.com/rss/markets-106.rss",
        "https://www.livemint.com/rss/markets",
    ],
    "world": [
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "http://feeds.reuters.com/reuters/businessNews",
    ],
}

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    """Strip HTML tags and decode entities (&amp; -> &, &#39; -> ', &nbsp; -> space)."""
    text = html.unescape(_TAG_RE.sub("", s or ""))
    return text.replace("\xa0", " ").strip()


def _normalize_entry(entry: dict, source: str) -> dict:
    """Map a feedparser entry (dict-like) to our normalized item shape."""
    return {
        "title": _strip_html(entry.get("title", "")),
        "summary": _strip_html(entry.get("summary", entry.get("description", ""))),
        "url": entry.get("link", "") or "",
        "source": source,
        "published_at": entry.get("published", entry.get("updated", "")) or "",
    }


def _dedupe(items: list[dict]) -> list[dict]:
    """Drop items with a duplicate title (case-insensitive), keep first seen."""
    seen: set[str] = set()
    out: list[dict] = []
    for it in items:
        key = (it.get("title") or "").strip().lower()
        if key and key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _matches_query(item: dict, query: str) -> bool:
    q = query.lower().strip()
    if not q:
        return False
    hay = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    return q in hay


# Friendly source label per feed host.
_SOURCE_LABELS = {
    "moneycontrol": "Moneycontrol",
    "indiatimes": "Economic Times",
    "business-standard": "Business Standard",
    "livemint": "LiveMint",
    "dowjones": "MarketWatch",
    "cnbc": "CNBC",
    "reuters": "Reuters",
}


def _source_for(url: str) -> str:
    for needle, label in _SOURCE_LABELS.items():
        if needle in url:
            return label
    return "News"


def fetch_feed_items(scope: str, limit: int = 40) -> list[dict]:
    """Fetch + normalize + dedupe items for a scope ('india' | 'world').

    Never raises: a feed that errors or returns nothing is skipped.
    """
    items: list[dict] = []
    for url in FEEDS.get(scope, []):
        try:
            parsed = feedparser.parse(url)
            source = _source_for(url)
            for entry in getattr(parsed, "entries", []):
                items.append(_normalize_entry(entry, source))
        except Exception:
            continue  # graceful: skip this feed
    return _dedupe(items)[:limit]


def _fetch_api_news(query: str, limit: int) -> list[dict]:
    """Optional free-tier enrichment via GNews. No key -> []. Never raises."""
    key = os.getenv("NEWS_API_KEY")
    if not key:
        return []
    try:
        # Lazy import: the API path is optional, so `requests` is only needed
        # when a key is configured (RSS-only installs need not have it).
        import requests
        resp = requests.get(
            "https://gnews.io/api/v4/search",
            params={"q": query, "lang": "en", "max": limit, "apikey": key},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        articles = resp.json().get("articles", [])
        return [{
            "title": _strip_html(a.get("title", "")),
            "summary": _strip_html(a.get("description", "")),
            "url": a.get("url", ""),
            "source": (a.get("source") or {}).get("name", "GNews"),
            "published_at": a.get("publishedAt", ""),
        } for a in articles]
    except Exception:
        return []


def _google_publisher(entry) -> str:
    """Best-effort publisher name from a Google News RSS entry's <source> tag."""
    src = entry.get("source")
    if isinstance(src, dict):
        return src.get("title") or "Google News"
    return "Google News"


def _fetch_google_news(query: str, limit: int = 40) -> list[dict]:
    """Per-stock news via Google News RSS search (free, no API key, India-localized).

    Google already matched the query, so results are trusted as-is (not
    re-filtered against the symbol). Never raises — a failure returns [].
    """
    import urllib.parse
    try:
        url = (
            "https://news.google.com/rss/search?q="
            + urllib.parse.quote(query)
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        )
        parsed = feedparser.parse(url)
        return [
            _normalize_entry(e, _google_publisher(e))
            for e in getattr(parsed, "entries", [])
        ][:limit]
    except Exception:
        return []


def fetch_stock_news(query: str, limit: int = 25) -> list[dict]:
    """News for a stock symbol.

    Primary source is a Google News RSS search (real per-ticker coverage,
    biased toward financial news). The India/world market RSS pool (filtered
    by symbol) and the optional free-tier GNews API supplement it. Deduped.
    """
    google = _fetch_google_news(f"{query} share price NSE", limit=40)
    pool = fetch_feed_items("india", limit=80) + fetch_feed_items("world", limit=40)
    matched = google + [it for it in pool if _matches_query(it, query)]
    matched += _fetch_api_news(query, limit)
    return _dedupe(matched)[:limit]
