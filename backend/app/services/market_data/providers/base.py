"""
Base provider class for market data
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app.core.logger import get_logger
from app.schemas.market import OHLCVData, TickData

_logger = get_logger(__name__)


class BaseMarketDataProvider(ABC):
    """
    Abstract base class for market data providers
    """

    def __init__(self, api_key: str, base_url: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.name = self.__class__.__name__
        self.rate_limit = 100  # requests per minute

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> List[OHLCVData]:
        """
        Fetch OHLCV candlestick data

        Args:
            symbol: Trading symbol (e.g., 'XAUUSD')
            timeframe: Candlestick timeframe (1m, 5m, 1h, 4h, 1d)
            limit: Number of candles to fetch

        Returns:
            List of OHLCV data
        """
        pass

    @abstractmethod
    async def fetch_latest_tick(self, symbol: str) -> TickData:
        """
        Fetch latest tick data (bid/ask/price)

        Args:
            symbol: Trading symbol

        Returns:
            Latest tick data
        """
        pass

    @abstractmethod
    async def get_available_symbols(self) -> List[str]:
        """
        Get list of available symbols from provider

        Returns:
            List of symbol codes
        """
        pass

    async def validate_connection(self) -> bool:
        """
        Test connection to provider API

        Returns:
            True if connection successful
        """
        try:
            symbols = await self.get_available_symbols()
            return len(symbols) > 0
        except Exception as e:
            _logger.error(f"Connection validation failed: {e}")
            return False
