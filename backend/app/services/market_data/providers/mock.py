"""
Mock Market Data Provider for testing
"""

import random
from datetime import UTC, datetime, timedelta
from typing import List, Optional

from app.schemas.market import OHLCVData, TickData
from app.services.market_data.providers.base import BaseMarketDataProvider


class MockMarketDataProvider(BaseMarketDataProvider):
    """Mock provider that returns simulated market data"""

    name = "Mock Provider"

    BASE_PRICES = {
        # Gold & primary instrument
        "XAUUSD":     2050.00,
        # Dollar & rates
        "DXY":         104.50,
        "US10Y":         4.35,   # yield %
        "US02Y":         4.85,   # yield %
        # Equities
        "SPX":        5250.00,
        "NDX":       18400.00,
        # Volatility
        "VIX":          15.50,
        # Forex
        "EURUSD":        1.085,
        "GBPUSD":        1.275,
        "USDJPY":      145.50,
        "AUDUSD":        0.658,
        "NZDUSD":        0.605,
        "USDCAD":        1.355,
        "USDCHF":        0.875,
        # Commodities
        "DCOILWTICO":   80.00,
    }

    SYMBOLS = [
        "XAUUSD", "DXY", "US10Y", "US02Y", "SPX", "NDX", "VIX",
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
        "DCOILWTICO",
    ]

    def __init__(self, api_key: str = "mock", seed: Optional[int] = None):
        self.api_key = api_key
        # Use a dedicated Random instance so tests can pass seed=42 without
        # affecting the global random state.
        self._rng = random.Random(seed)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 20,
    ) -> List[OHLCVData]:
        base_price = self.BASE_PRICES.get(symbol, 100.0)
        current_time = datetime.now(UTC)
        data = []

        for i in range(limit, 0, -1):
            timestamp = current_time - timedelta(hours=i)
            noise = self._rng.uniform(-0.02, 0.02)
            open_price = base_price * (1 + self._rng.uniform(-0.01, 0.01))
            close_price = open_price * (1 + noise)
            high_price = max(open_price, close_price) * (1 + abs(self._rng.uniform(0, 0.005)))
            low_price = min(open_price, close_price) * (1 - abs(self._rng.uniform(0, 0.005)))
            volume = self._rng.uniform(1_000_000, 5_000_000)

            data.append(OHLCVData(
                symbol=symbol,
                timeframe=timeframe,
                open=round(open_price, 5),
                high=round(high_price, 5),
                low=round(low_price, 5),
                close=round(close_price, 5),
                volume=round(volume),
                timestamp=timestamp,
                data_source="mock",
            ))

        return data

    async def fetch_latest_tick(self, symbol: str) -> TickData:
        base_price = self.BASE_PRICES.get(symbol, 100.0)
        spread_pips = self._rng.uniform(0.5, 2.0) / 10_000
        mid_price = base_price * (1 + self._rng.uniform(-0.001, 0.001))
        bid = round(mid_price - spread_pips, 5)
        ask = round(mid_price + spread_pips, 5)

        return TickData(
            symbol=symbol,
            bid=bid,
            ask=ask,
            price=round((bid + ask) / 2, 5),
            volume=self._rng.uniform(100_000, 500_000),
            timestamp=datetime.now(UTC),
            data_source="mock",
        )

    async def get_available_symbols(self) -> List[str]:
        return self.SYMBOLS

    async def validate_connection(self) -> bool:
        return True
