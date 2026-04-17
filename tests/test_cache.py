"""Regression tests for backend in-memory cache."""

import asyncio
import sys
import unittest

sys.path.insert(0, "backend")


class CacheTest(unittest.TestCase):
    def setUp(self):
        from services import cache
        cache._store.clear()

    def test_async_fn_is_awaited_not_stored_as_coroutine(self):
        """Regression: async fn must be awaited, not wrapped in to_thread."""
        from services.cache import cached

        async def _fetch():
            return "hello"

        async def run():
            first = await cached("k", ttl=60, fn=_fetch)
            second = await cached("k", ttl=60, fn=_fetch)
            return first, second

        first, second = asyncio.run(run())
        self.assertEqual(first, "hello")
        self.assertEqual(second, "hello")

    def test_sync_fn_still_works(self):
        from services.cache import cached

        calls = {"n": 0}

        def _fetch():
            calls["n"] += 1
            return 42

        async def run():
            a = await cached("k2", ttl=60, fn=_fetch)
            b = await cached("k2", ttl=60, fn=_fetch)
            return a, b

        a, b = asyncio.run(run())
        self.assertEqual(a, 42)
        self.assertEqual(b, 42)
        self.assertEqual(calls["n"], 1, "cache should only call fn once")


if __name__ == "__main__":
    unittest.main()
