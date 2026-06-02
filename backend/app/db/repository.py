"""
Data Access Layer — repository pattern for market data.
"""

from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy import select, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.db.models import MarketDataOHLCV, TickDataRecord
from app.schemas.market import OHLCVData, TickData

logger = get_logger(__name__)


class OHLCVRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, candle: OHLCVData) -> None:
        """Insert a candle; skip silently if (symbol, timeframe, timestamp) already exists."""
        stmt = (
            pg_insert(MarketDataOHLCV)
            .values(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                timestamp=candle.timestamp,
                data_source=candle.data_source,
            )
            .on_conflict_do_nothing(
                index_elements=["symbol", "timeframe", "timestamp"]
            )
        )
        await self.session.execute(stmt)

    async def upsert_many(self, candles: List[OHLCVData]) -> int:
        """Bulk upsert — returns number of rows actually inserted."""
        if not candles:
            return 0

        rows = [
            {
                "symbol": c.symbol,
                "timeframe": c.timeframe,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "timestamp": c.timestamp,
                "data_source": c.data_source,
            }
            for c in candles
        ]
        stmt = (
            pg_insert(MarketDataOHLCV)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["symbol", "timeframe", "timestamp"])
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[OHLCVData]:
        """Fetch candles from DB, newest first then reversed to chronological order."""
        q = (
            select(MarketDataOHLCV)
            .where(
                MarketDataOHLCV.symbol == symbol,
                MarketDataOHLCV.timeframe == timeframe,
            )
            .order_by(desc(MarketDataOHLCV.timestamp))
            .limit(limit)
        )
        if start:
            q = q.where(MarketDataOHLCV.timestamp >= start)
        if end:
            q = q.where(MarketDataOHLCV.timestamp <= end)

        result = await self.session.execute(q)
        rows = result.scalars().all()

        return [
            OHLCVData(
                symbol=row.symbol,
                timeframe=row.timeframe,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
                timestamp=row.timestamp,
                data_source=row.data_source,
            )
            for row in reversed(rows)   # chronological
        ]

    async def get_latest_timestamp(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """Return the most recent candle timestamp for a symbol/timeframe."""
        q = (
            select(MarketDataOHLCV.timestamp)
            .where(
                MarketDataOHLCV.symbol == symbol,
                MarketDataOHLCV.timeframe == timeframe,
            )
            .order_by(desc(MarketDataOHLCV.timestamp))
            .limit(1)
        )
        result = await self.session.execute(q)
        row = result.scalar_one_or_none()
        return row


class TickRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, tick: TickData) -> None:
        record = TickDataRecord(
            symbol=tick.symbol,
            bid=tick.bid,
            ask=tick.ask,
            price=tick.price,
            spread=round(tick.ask - tick.bid, 8),
            volume=tick.volume,
            timestamp=tick.timestamp,
            data_source=tick.data_source,
        )
        self.session.add(record)

    async def get_latest(self, symbol: str) -> Optional[TickData]:
        q = (
            select(TickDataRecord)
            .where(TickDataRecord.symbol == symbol)
            .order_by(desc(TickDataRecord.timestamp))
            .limit(1)
        )
        result = await self.session.execute(q)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return TickData(
            symbol=row.symbol,
            bid=row.bid,
            ask=row.ask,
            price=row.price,
            volume=row.volume,
            timestamp=row.timestamp,
            data_source=row.data_source,
        )
