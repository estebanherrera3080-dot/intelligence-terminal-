"""
Async Redis client with graceful degradation.

get_redis() returns a connected client or None if Redis is unavailable.
Callers must handle None by falling back to in-memory storage — they must
never raise an exception because Redis is down.
"""

import asyncio
import logging
from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[Redis] = None


async def get_redis() -> Optional[Redis]:
    """
    Return connected Redis client, or None if unreachable.
    - Caches the connected client; reconnects only when client is None.
    - Does NOT cache failures: if Redis is down, next call retries.
    """
    global _client

    if _client is not None:
        return _client

    try:
        client: Redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,
        )
        await asyncio.wait_for(client.ping(), timeout=2.0)
        _client = client
        logger.info(f"Redis connected → {settings.redis_url}")
    except Exception as exc:
        logger.warning(
            f"Redis unavailable ({exc.__class__.__name__}: {exc}) "
            "— TickStore will use in-memory fallback"
        )
        _client = None

    return _client


async def close_redis() -> None:
    """Gracefully close the Redis connection on app shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("Redis connection closed")


async def ping_redis() -> bool:
    """True if Redis is currently reachable."""
    try:
        client = await get_redis()
        if client is None:
            return False
        await asyncio.wait_for(client.ping(), timeout=1.0)
        return True
    except Exception:
        return False
