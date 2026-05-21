"""Tests for services/cache.py — in-memory fallback path (no Redis configured)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import pytest
from unittest.mock import patch

# Force the in-memory path by ensuring Redis env vars are absent
@pytest.fixture(autouse=True)
def no_redis(monkeypatch):
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "")
    # Also clear the lru_cache on settings so monkeypatched env is picked up
    from config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_cache_miss_calls_fn():
    from services.cache import cached, _store
    _store.clear()

    calls = []
    def fn():
        calls.append(1)
        return 42

    result = run(cached("test:miss", ttl=60, fn=fn))
    assert result == 42
    assert len(calls) == 1


def test_cache_hit_skips_fn():
    from services.cache import cached, _store
    _store.clear()

    calls = []
    def fn():
        calls.append(1)
        return 99

    run(cached("test:hit", ttl=60, fn=fn))
    result = run(cached("test:hit", ttl=60, fn=fn))
    assert result == 99
    assert len(calls) == 1  # fn called only once


def test_cache_clear_evicts():
    from services.cache import cached, cache_clear, _store
    _store.clear()

    run(cached("test:clear", ttl=60, fn=lambda: "v1"))
    cache_clear("test:clear")

    calls = []
    def fn2():
        calls.append(1)
        return "v2"

    result = run(cached("test:clear", ttl=60, fn=fn2))
    assert result == "v2"
    assert len(calls) == 1


def test_expired_entry_refetches():
    from services.cache import cached, _store
    _store.clear()

    _store["test:exp"] = ("stale", 0.0)  # already expired

    result = run(cached("test:exp", ttl=60, fn=lambda: "fresh"))
    assert result == "fresh"


def test_lru_cap():
    from services.cache import cached, _store, _MAX_LOCAL
    _store.clear()

    for i in range(_MAX_LOCAL + 5):
        run(cached(f"key:{i}", ttl=3600, fn=lambda i=i: i))

    assert len(_store) <= _MAX_LOCAL
