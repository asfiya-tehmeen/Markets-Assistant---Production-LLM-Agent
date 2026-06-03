"""Redis-backed price/question caching and per-IP rate limiting.

Everything here is fail-open: if Redis is unreachable, caching is skipped and rate limiting
allows the request, so the app keeps working in local dev without Redis.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import redis

from app.config import get_settings
from app.tools.prices import get_price

_redis_client: "redis.Redis | None" = None
_redis_initialised = False


def get_redis() -> "redis.Redis | None":
    """Return a connected Redis client, or None if unavailable (cached after first try)."""
    global _redis_client, _redis_initialised
    if _redis_initialised:
        return _redis_client
    _redis_initialised = True
    try:
        client = redis.Redis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=1, socket_timeout=1, decode_responses=True,
        )
        client.ping()
        _redis_client = client
    except Exception:
        _redis_client = None
    return _redis_client


# --- Price cache --------------------------------------------------------------------------

def get_price_cached(symbol: str, vs_currency: str = "usd") -> dict:
    """``get_price`` with a short-TTL Redis cache. Only successful lookups are cached."""
    settings = get_settings()
    client = get_redis()
    key = f"price:{symbol.strip().lower()}:{vs_currency.strip().lower()}"

    if client is not None:
        try:
            hit = client.get(key)
            if hit:
                return {**json.loads(hit), "cached": True}
        except Exception:
            pass

    result = get_price(symbol, vs_currency)

    if client is not None and result.get("ok"):
        try:
            client.setex(key, settings.price_cache_ttl, json.dumps(result, default=str))
        except Exception:
            pass
    return result


# --- Question cache -----------------------------------------------------------------------

def _question_key(question: str) -> str:
    digest = hashlib.sha256(question.strip().lower().encode()).hexdigest()
    return f"q:{digest}"


def get_cached_answer(question: str) -> dict | None:
    """Return a previously cached structured answer for an identical question, if any."""
    client = get_redis()
    if client is None:
        return None
    try:
        hit = client.get(_question_key(question))
        return json.loads(hit) if hit else None
    except Exception:
        return None


def cache_answer(question: str, response: dict) -> None:
    """Cache a structured answer under the question hash (short TTL to avoid stale prices)."""
    client = get_redis()
    if client is None:
        return
    try:
        client.setex(_question_key(question), get_settings().question_cache_ttl,
                     json.dumps(response, default=str))
    except Exception:
        pass


# --- Rate limiting ------------------------------------------------------------------------

def check_rate_limit(client_ip: str) -> tuple[bool, int]:
    """Fixed-window per-IP limiter. Returns ``(allowed, remaining)``; fail-open if Redis down."""
    settings = get_settings()
    limit = settings.rate_limit_per_minute
    client = get_redis()
    if client is None:
        return True, limit
    try:
        bucket = int(time.time() // 60)
        key = f"rl:{client_ip}:{bucket}"
        count = client.incr(key)
        if count == 1:
            client.expire(key, 60)
        return count <= limit, max(0, limit - count)
    except Exception:
        return True, limit
