"""
Market Data Service — orchestrates provider fetching and DB persistence.
"""

from datetime import datetime, UTC, timedelta
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.db.repository import OHLCVRepository, TickRepository
from app.schemas.market import OHLCVData, TickData
from app.services.market_data.providers.base import BaseMarketDataProvider

logger = get_logger(__name__)

# All instruments tracked by the terminal
TRACKED_SYMBOLS = ["XAUUSD", "DXY", "US10Y", "US02Y", "SPX", "NDX", "VIX"]
TRACKED_TIMEFRAMES = ["1h", "4h", "1d"]

# Minimum candles in DB before skipping a fresh provider fetch
_MIN_CACHED_CANDLES = 50


class MarketDataService:
    """
    Single entry-point for all market data operations.

    Strategy:
    - DB is the source of truth for historical data.
    - Provider is queried when DB is empty or data is stale.
    - Writes are always async to DB for future queries.
    """

    def __init__(self, provider: BaseMarketDataProvider, db: AsyncSession) -> None:
        self.provider = provider
        self.ohlcv_repo = OHLCVRepository(db)
        self.tick_repo = TickRepository(db)

    # ------------------------------------------------------------------ #
    #  OHLCV                                                               #
    # ------------------------------------------------------------------ #

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
    ) -> List[OHLCVData]:
        """
        Return OHLCV candles.
        Serves from DB when warm; fetches from provider and populates DB otherwise.
        """
        try:
            cached = await self.ohlcv_repo.get_candles(symbol, timeframe, limit)
            if len(cached) >= min(limit, _MIN_CACHED_CANDLES):
                return cached[-limit:]
        except Exception as e:
            logger.warning(f"DB unavailable, falling back to provider: {e}")
            cached = []

        logger.info(f"Cache miss — fetching {symbol}/{timeframe} from provider")
        fresh = await self.provider.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)

        if fresh:
            await self._persist_ohlcv(fresh)

        return fresh

    async def refresh_symbol(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
    ) -> List[OHLCVData]:
        """Force-fetch from provider regardless of cache state."""
        data = await self.provider.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
        if data:
            await self._persist_ohlcv(data)
        return data

    async def refresh_all(self, limit: int = 200) -> dict:
        """Refresh all tracked symbols across all tracked timeframes."""
        results: dict = {}
        for symbol in TRACKED_SYMBOLS:
            results[symbol] = {}
            for tf in TRACKED_TIMEFRAMES:
                try:
                    data = await self.refresh_symbol(symbol, tf, limit)
                    results[symbol][tf] = len(data)
                    logger.info(f"Refreshed {symbol}/{tf}: {len(data)} candles")
                except Exception as e:
                    logger.error(f"Failed to refresh {symbol}/{tf}: {e}")
                    results[symbol][tf] = 0
        return results

    async def _persist_ohlcv(self, candles: List[OHLCVData]) -> None:
        try:
            inserted = await self.ohlcv_repo.upsert_many(candles)
            logger.debug(f"Persisted {inserted}/{len(candles)} candles")
        except Exception as e:
            logger.warning(f"Failed to persist OHLCV to DB: {e}")

    # ------------------------------------------------------------------ #
    #  TICKS                                                               #
    # ------------------------------------------------------------------ #

    async def get_latest_tick(self, symbol: str) -> TickData:
        """Return latest tick — always fetches live from provider."""
        tick = await self.provider.fetch_latest_tick(symbol)
        try:
            await self.tick_repo.save(tick)
        except Exception as e:
            logger.warning(f"Failed to persist tick for {symbol}: {e}")
        return tick

    async def get_latest_ticks_all(self) -> dict:
        """Fetch latest tick for every tracked symbol."""
        ticks = {}
        for symbol in TRACKED_SYMBOLS:
            try:
                tick = await self.get_latest_tick(symbol)
                ticks[symbol] = {
                    "price": tick.price,
                    "bid": tick.bid,
                    "ask": tick.ask,
                    "spread": round(tick.ask - tick.bid, 8),
                    "volume": tick.volume,
                    "timestamp": tick.timestamp.isoformat(),
                    "source": tick.data_source,
                }
            except Exception as e:
                logger.error(f"Failed to fetch tick for {symbol}: {e}")
        return ticks

    # ------------------------------------------------------------------ #
    #  Utility                                                             #
    # ------------------------------------------------------------------ #

    async def get_available_symbols(self) -> List[str]:
        return await self.provider.get_available_symbols()

    async def health_check(self) -> dict:
        connected = await self.provider.validate_connection()
        return {
            "status": "healthy" if connected else "unhealthy",
            "provider": self.provider.name,
            "connected": connected,
            "tracked_symbols": TRACKED_SYMBOLS,
        }
