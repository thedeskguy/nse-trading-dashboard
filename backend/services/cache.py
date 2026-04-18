"""
Two-tier cache: Upstash Redis (HTTP) when configured, in-memory LRU fallback otherwise.

Set UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN in env to enable Redis.
Without those vars the service falls back to a process-local dict (dev / single-replica).
"""
import asyncio
import base64
import inspect
import pickle
import time
from typing import Any, Callable

import httpx

_store: dict[str, tuple[Any, float]] = {}  # fallback: key -> (value, expires_at)
_MAX_LOCAL = 256  # evict oldest when cap is reached


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings():
    from config import get_settings
    return get_settings()


def _use_redis() -> bool:
    s = _settings()
    return bool(s.UPSTASH_REDIS_REST_URL and s.UPSTASH_REDIS_REST_TOKEN)


def _encode(obj: Any) -> str:
    return base64.b64encode(pickle.dumps(obj, protocol=4)).decode()


def _decode(s: str) -> Any:
    return pickle.loads(base64.b64decode(s))


async def _redis_cmd(cmd: list) -> Any:
    s = _settings()
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(
            s.UPSTASH_REDIS_REST_URL,
            json=cmd,
            headers={"Authorization": f"Bearer {s.UPSTASH_REDIS_REST_TOKEN}"},
        )
        resp.raise_for_status()
        return resp.json().get("result")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def cached(key: str, ttl: int, fn: Callable) -> Any:
    """Return cached value for `key`, calling `fn` on miss and storing for `ttl` seconds."""
    if _use_redis():
        try:
            raw = await _redis_cmd(["GET", key])
            if raw is not None:
                return _decode(raw)
        except Exception:
            pass  # Redis unavailable — compute and try to store below
    else:
        now = time.time()
        if key in _store and _store[key][1] > now:
            return _store[key][0]

    # Cache miss — compute
    result = await fn() if inspect.iscoroutinefunction(fn) else await asyncio.to_thread(fn)

    if _use_redis():
        try:
            await _redis_cmd(["SET", key, _encode(result), "EX", str(ttl)])
        except Exception:
            pass  # best-effort; caller still gets the result
    else:
        if len(_store) >= _MAX_LOCAL:
            oldest_key = min(_store, key=lambda k: _store[k][1])
            del _store[oldest_key]
        _store[key] = (result, time.time() + ttl)

    return result


async def _redis_del(key: str) -> None:
    try:
        await _redis_cmd(["DEL", key])
    except Exception:
        pass


def cache_clear(key: str) -> None:
    """Evict `key` from cache (local store immediately; Redis via background task)."""
    _store.pop(key, None)
    if _use_redis():
        try:
            asyncio.get_event_loop().create_task(_redis_del(key))
        except RuntimeError:
            pass  # no running loop (e.g. called from sync context at import time)
