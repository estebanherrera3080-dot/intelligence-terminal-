"""
TickStore — Redis-backed cache for real-time ticks and OHLCV data.

Write path  : Celery tasks call set_tick() / set_snapshot() after every
              provider fetch. HTTP endpoints never call the provider.

Read path   : HTTP endpoints call get_snapshot() / get_tick(). Zero
              provider API calls on every frontend poll.

Fallback    : When Redis is unavailable, all operations use an in-process
              dict with manual TTL. Data survives a Redis restart for up
              to TTL seconds without any service interruption.

Provider independence: this module imports nothing from the provider layer.
Swapping Twelve Data → Polygon requires no changes here.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Redis key patterns ────────────────────────────────────────────── #
_K_TICK = "tick:{symbol}"           # single symbol tick
_K_SNAPSHOT = "ticks:snapshot"      # all symbols in one key
_K_OHLCV = "ohlcv:{symbol}:{tf}"   # candle list per symbol/timeframe

# ── TTLs in seconds ───────────────────────────────────────────────── #
# Tier1 refreshes every 5 min → 10 min TTL gives 1 missed cycle buffer
_TTL_TICK: int = 600
_TTL_SNAPSHOT: int = 600
_TTL_OHLCV: Dict[str, int] = {
    "1h": 3900,    # 65 min  (Celery refreshes every 65 min)
    "4h": 14400,   # 4 h
    "1d": 86400,   # 24 h
}
_TTL_OHLCV_DEFAULT: int = 3900

# ── In-memory fallback storage ────────────────────────────────────── #
_mem: Dict[str, Dict[str, Any]] = {}  # key → {data, expires_at}


def _mem_get(key: str) -> Optional[Any]:
    entry = _mem.get(key)
    if entry is None:
        return None
    if time.monotonic() > entry["expires_at"]:
        _mem.pop(key, None)
        return None
    return entry["data"]


def _mem_set(key: str, data: Any, ttl: int) -> None:
    _mem[key] = {"data": data, "expires_at": time.monotonic() + ttl}


# ── TickStore ─────────────────────────────────────────────────────── #

class TickStore:
    """
    Thin async wrapper around Redis for market data caching.
    Safe to call from FastAPI request handlers and Celery async tasks.
    """

    # ── Ticks ─────────────────────────────────────────────────────── #

    async def set_tick(self, symbol: str, payload: dict) -> None:
        """Write a single tick to cache. Called by Celery after provider fetch."""
        key = _K_TICK.format(symbol=symbol.upper())
        await self._set(key, payload, _TTL_TICK)

    async def get_tick(self, symbol: str) -> Optional[dict]:
        """Read a single tick. Returns None if cache is cold for this symbol."""
        key = _K_TICK.format(symbol=symbol.upper())
        return await self._get(key)

    async def set_snapshot(self, snapshot: dict) -> None:
        """Write full all-symbols dict. Called by Celery after each tier run."""
        await self._set(_K_SNAPSHOT, snapshot, _TTL_SNAPSHOT)

    async def get_snapshot(self) -> Optional[dict]:
        """
        Read full all-symbols dict.
        Returns None only if cache is completely cold (no Celery run yet).
        """
        return await self._get(_K_SNAPSHOT)

    # ── OHLCV ─────────────────────────────────────────────────────── #

    async def set_ohlcv(self, symbol: str, timeframe: str, candles: List[dict]) -> None:
        """Cache serialized candle list. Called by Celery after OHLCV refresh."""
        key = _K_OHLCV.format(symbol=symbol.upper(), tf=timeframe)
        ttl = _TTL_OHLCV.get(timeframe, _TTL_OHLCV_DEFAULT)
        await self._set(key, candles, ttl)

    async def get_ohlcv(self, symbol: str, timeframe: str) -> Optional[List[dict]]:
        """Read cached candle list. Returns None on cache miss."""
        key = _K_OHLCV.format(symbol=symbol.upper(), tf=timeframe)
        return await self._get(key)

    # ── Status ────────────────────────────────────────────────────── #

    async def status(self) -> dict:
        """Cache health summary — used by /market/health endpoint."""
        from app.core.redis_client import ping_redis
        redis_ok = await ping_redis()
        snapshot = await self.get_snapshot()
        return {
            "redis": "connected" if redis_ok else "unavailable",
            "fallback_active": not redis_ok,
            "snapshot_cached": snapshot is not None,
            "symbols_cached": list(snapshot.keys()) if snapshot else [],
        }

    # ── Internal Redis/memory helpers ─────────────────────────────── #

    async def _get(self, key: str) -> Optional[Any]:
        try:
            from app.core.redis_client import get_redis
            r = await get_redis()
            if r is not None:
                raw = await r.get(key)
                if raw is not None:
                    return json.loads(raw)
        except Exception as exc:
            logger.debug(f"Redis GET {key} failed: {exc}")
        return _mem_get(key)

    async def _set(self, key: str, data: Any, ttl: int) -> None:
        try:
            from app.core.redis_client import get_redis
            r = await get_redis()
            if r is not None:
                await r.setex(key, ttl, json.dumps(data, default=str))
                return
        except Exception as exc:
            logger.debug(f"Redis SET {key} failed: {exc}")
        _mem_set(key, data, ttl)


# Module-level singleton — import this everywhere
tick_store = TickStore()
