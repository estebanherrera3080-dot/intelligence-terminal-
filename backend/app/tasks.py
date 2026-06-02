"""
Celery tasks — market data polling and WebSocket broadcast.
"""

import asyncio
from typing import Optional

from celery import shared_task
from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.services.market_data.providers import get_active_provider
from app.services.market_data.service import TRACKED_SYMBOLS, TRACKED_TIMEFRAMES

logger = get_task_logger(__name__)


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ------------------------------------------------------------------ #
#  Tick polling                                                        #
# ------------------------------------------------------------------ #

@celery_app.task(name="app.tasks.fetch_all_ticks", bind=True, max_retries=3)
def fetch_all_ticks(self):
    """
    Fetch latest tick for every tracked symbol and broadcast via WebSocket.
    Runs every 60 s (see celery_app.beat_schedule).
    """
    from app.services.websocket.manager import ws_manager

    async def _inner():
        provider = get_active_provider()
        results = {}

        for symbol in TRACKED_SYMBOLS:
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
                results[symbol] = payload
                await ws_manager.broadcast_tick(symbol, payload)
            except Exception as e:
                logger.warning(f"Tick fetch failed for {symbol}: {e}")

        return results

    try:
        return _run(_inner())
    except Exception as exc:
        logger.error(f"fetch_all_ticks failed: {exc}")
        raise self.retry(exc=exc, countdown=10)


# ------------------------------------------------------------------ #
#  OHLCV refresh                                                       #
# ------------------------------------------------------------------ #

@celery_app.task(name="app.tasks.refresh_ohlcv", bind=True, max_retries=2)
def refresh_ohlcv(self, timeframe: str = "1h", limit: int = 10):
    """
    Refresh recent candles for all tracked symbols.
    Called by beat at intervals defined in celery_app.beat_schedule.
    """
    async def _inner():
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import AsyncSessionLocal
        from app.services.market_data.service import MarketDataService

        provider = get_active_provider()
        results = {}

        async with AsyncSessionLocal() as session:
            service = MarketDataService(provider=provider, db=session)
            for symbol in TRACKED_SYMBOLS:
                try:
                    data = await service.refresh_symbol(symbol, timeframe, limit)
                    results[symbol] = len(data)
                except Exception as e:
                    logger.warning(f"OHLCV refresh failed for {symbol}/{timeframe}: {e}")
                    results[symbol] = 0

        return results

    try:
        return _run(_inner())
    except Exception as exc:
        logger.error(f"refresh_ohlcv failed: {exc}")
        raise self.retry(exc=exc, countdown=30)


# ------------------------------------------------------------------ #
#  Historical backfill (one-shot, triggered on startup)               #
# ------------------------------------------------------------------ #

@celery_app.task(name="app.tasks.backfill_history")
def backfill_history(limit: int = 500):
    """
    Backfill historical OHLCV for all symbols/timeframes.
    Trigger manually or once after first deploy:
        celery -A app.tasks call app.tasks.backfill_history
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
                        logger.info(f"Backfill {symbol}/{tf}: {len(data)} candles")
                    except Exception as e:
                        logger.error(f"Backfill failed {symbol}/{tf}: {e}")

        return {"total_candles_stored": total}

    return _run(_inner())
