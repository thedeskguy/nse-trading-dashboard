import time
import asyncio
import inspect
from typing import Any, Callable

_store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)


async def cached(key: str, ttl: int, fn: Callable) -> Any:
    now = time.time()
    if key in _store and _store[key][1] > now:
        return _store[key][0]
    if inspect.iscoroutinefunction(fn):
        result = await fn()
    else:
        result = await asyncio.to_thread(fn)
    _store[key] = (result, now + ttl)
    return result


def cache_clear(key: str):
    _store.pop(key, None)
