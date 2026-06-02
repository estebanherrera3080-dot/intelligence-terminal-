"""
Celery tasks — market data polling, cache writes, and WebSocket broadcast.

Data flow:
  Provider (Twelve Data / Mock)
      → fetch_ticks_tier1 / fetch_ticks_tier2
          → TickStore.set_tick()   (Redis → memory fallback)
          → TickStore.set_snapshot()
          → ws_manager.broadcast_tick()
      → refresh_ohlcv
          → MarketDataService.refresh_symbol()  (DB persist)
          → TickStore.set_ohlcv()               (Redis cache)

HTTP endpoints read exclusively from TickStore — never from provider.
"""

import asyncio

from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.services.market_data.providers import get_active_provider
from app.services.market_data.service import TRACKED_SYMBOLS, TRACKED_TIMEFRAMES

logger = get_task_logger(__name__)

# ── Symbol tiers ──────────────────────────────────────────────────── #
# Tier 1: primary instruments — poll every 5 min (3 credits/cycle)
TIER1_SYMBOLS = ["XAUUSD", "DXY", "VIX"]
# Tier 2: macro context — poll every 15 min (4 credits/cycle)
TIER2_SYMBOLS = ["US10Y", "US02Y", "SPX", "NDX"]


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ── Shared tick fetch logic ───────────────────────────────────────── #

async def _fetch_and_cache_ticks(symbols: list) -> dict:
    """
    1. Fetch ticks from active provider for given symbols.
    2. Write each tick to TickStore (Redis → memory fallback).
    3. Merge into the all-symbols snapshot and overwrite it.
    4. Broadcast via WebSocket to connected clients.

    Returns dict of {symbol: price} for logging.
    """
    from app.services.cache.tick_store import tick_store
    from app.services.websocket.manager import ws_manager

    provider = get_active_provider()
    fetched: dict = {}

    for symbol in symbols:
        try:
            tick = await provider.fetch_latest_tick(symbol)
            payload = {
                "price":     tick.price,
                "bid":       tick.bid,
                "ask":       tick.ask,
                "spread":    round(tick.ask - tick.bid, 8),
                "volume":    tick.volume,
                "timestamp": tick.timestamp.isoformat(),
                "source":    tick.data_source,
            }
            await tick_store.set_tick(symbol, payload)
            fetched[symbol] = payload
            await ws_manager.broadcast_tick(symbol, payload)
            logger.info(f"[tick] {symbol} @ {tick.price:.4f}  source={tick.data_source}")
        except Exception as exc:
            logger.warning(f"[tick] {symbol} fetch failed: {exc}")

    # Merge new ticks into the full snapshot so /latest/all stays complete
    if fetched:
        existing = await tick_store.get_snapshot() or {}
        existing.update(fetched)
        await tick_store.set_snapshot(existing)

    return {s: d["price"] for s, d in fetched.items()}


# ── Tier 1: XAUUSD · DXY · VIX  (every 5 min) ───────────────────── #

@celery_app.task(name="app.tasks.fetch_ticks_tier1", bind=True, max_retries=3)
def fetch_ticks_tier1(self):
    """
    Fetch Tier 1 ticks (XAUUSD, DXY, VIX) and write to cache.
    Budget: 3 credits/run × 12 runs/h × 8 h/day = 288 credits/day.
    """
    try:
        return _run(_fetch_and_cache_ticks(TIER1_SYMBOLS))
    except Exception as exc:
        logger.error(f"fetch_ticks_tier1 failed: {exc}")
        raise self.retry(exc=exc, countdown=15)


# ── Tier 2: US10Y · US02Y · SPX · NDX  (every 15 min) ───────────── #

@celery_app.task(name="app.tasks.fetch_ticks_tier2", bind=True, max_retries=3)
def fetch_ticks_tier2(self):
    """
    Fetch Tier 2 ticks (US10Y, US02Y, SPX, NDX) and write to cache.
    Budget: 4 credits/run × 4 runs/h × 8 h/day = 128 credits/day.
    """
    try:
        return _run(_fetch_and_cache_ticks(TIER2_SYMBOLS))
    except Exception as exc:
        logger.error(f"fetch_ticks_tier2 failed: {exc}")
        raise self.retry(exc=exc, countdown=15)


# ── OHLCV refresh ─────────────────────────────────────────────────── #

@celery_app.task(name="app.tasks.refresh_ohlcv", bind=True, max_retries=2)
def refresh_ohlcv(self, timeframe: str = "1h", limit: int = 3):
    """
    Refresh recent candles for all tracked symbols.
    Persists to PostgreSQL (via MarketDataService) and caches in Redis.
    """
    async def _inner():
        from app.db.session import AsyncSessionLocal
        from app.services.cache.tick_store import tick_store
        from app.services.market_data.service import MarketDataService

        provider = get_active_provider()
        results: dict = {}

        async with AsyncSessionLocal() as session:
            service = MarketDataService(provider=provider, db=session)
            for symbol in TRACKED_SYMBOLS:
                try:
                    data = await service.refresh_symbol(symbol, timeframe, limit)
                    results[symbol] = len(data)
                    if data:
                        candles_json = [
                            {
                                "symbol":      c.symbol,
                                "timeframe":   c.timeframe,
                                "open":        c.open,
                                "high":        c.high,
                                "low":         c.low,
                                "close":       c.close,
                                "volume":      c.volume,
                                "timestamp":   c.timestamp.isoformat(),
                                "data_source": c.data_source,
                            }
                            for c in data
                        ]
                        await tick_store.set_ohlcv(symbol, timeframe, candles_json)
                    logger.info(f"[ohlcv] {symbol}/{timeframe}: {len(data)} candles refreshed")
                except Exception as exc:
                    logger.warning(f"[ohlcv] {symbol}/{timeframe} failed: {exc}")
                    results[symbol] = 0

        return results

    try:
        return _run(_inner())
    except Exception as exc:
        logger.error(f"refresh_ohlcv failed: {exc}")
        raise self.retry(exc=exc, countdown=30)


# ── Historical backfill (one-shot) ───────────────────────────────── #

@celery_app.task(name="app.tasks.backfill_history")
def backfill_history(limit: int = 500):
    """
    Backfill historical OHLCV for all symbols / timeframes.
    Run once after first deploy:
        celery -A app.tasks call app.tasks.backfill_history
    Cost: 7 symbols × 3 timeframes × 1 request = 21 API credits.
    """
    async def _inner():
        from app.db.session import AsyncSessionLocal
        from app.services.market_data.service import MarketDataService

        provider = get_active_provider()
        total = 0

        async with AsyncSessionLocal() as session:
            service = MarketDataService(provider=provider, db=session)
            for tf in TRACKED_TIMEFRAMES:
                for symbol in TRACKED_SYMBOLS:
                    try:
                        data = await service.refresh_symbol(symbol, tf, limit)
                        total += len(data)
                        logger.info(f"[backfill] {symbol}/{tf}: {len(data)} candles")
                    except Exception as exc:
                        logger.error(f"[backfill] {symbol}/{tf} failed: {exc}")

        return {"total_candles_stored": total}

    return _run(_inner())
