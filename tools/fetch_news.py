"""Free news fetcher: RSS backbone + optional free-tier API enrichment.

No paid APIs. If NEWS_API_KEY is absent, the API path is skipped silently and
RSS alone is used. Network functions are thin wrappers around feedparser; the
parsing/normalisation logic lives in pure helpers so it is unit-testable.
"""
import re

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
    return _TAG_RE.sub("", s or "").replace("&nbsp;", " ").strip()


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
