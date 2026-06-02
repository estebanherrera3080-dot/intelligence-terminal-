"""
Twelve Data market data provider.
https://twelvedata.com/docs

Free tier: 800 API credits/day, real-time & historical data.
"""

from datetime import UTC, datetime
from typing import List

import httpx

from app.core.logger import get_logger
from app.schemas.market import OHLCVData, TickData
from app.services.market_data.providers.base import BaseMarketDataProvider

logger = get_logger(__name__)

# Internal timeframe → Twelve Data interval mapping
_TF_MAP = {
    "1m":  "1min",
    "5m":  "5min",
    "15m": "15min",
    "30m": "30min",
    "1h":  "1h",
    "4h":  "4h",
    "1d":  "1day",
    "1w":  "1week",
}

# Internal symbol → Twelve Data symbol mapping
# Twelve Data uses slash notation for forex pairs and exact tickers for indices
_SYMBOL_MAP = {
    "XAUUSD": "XAU/USD",
    "DXY":    "DXY",
    "US10Y":  "TNX",       # CBOE 10-Year Treasury Note Yield Index
    "US02Y":  "IRX",       # CBOE 13-Week Treasury Bill (proxy for 2Y)
    "SPX":    "SPX",
    "NDX":    "NDX",
    "VIX":    "VIX",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
}

# Tracked institutional instruments
TRACKED_SYMBOLS = list(_SYMBOL_MAP.keys())


class TwelveDataProvider(BaseMarketDataProvider):
    """
    Production data provider using Twelve Data API.
    Falls back gracefully per-symbol on API errors.
    """

    name = "Twelve Data"

    def __init__(self, api_key: str = "demo"):
        super().__init__(api_key=api_key, base_url="https://api.twelvedata.com")

    def _resolve_symbol(self, symbol: str) -> str:
        return _SYMBOL_MAP.get(symbol, symbol)

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 200,
    ) -> List[OHLCVData]:
        td_symbol = self._resolve_symbol(symbol)
        td_interval = _TF_MAP.get(timeframe, timeframe)

        params = {
            "symbol":     td_symbol,
            "interval":   td_interval,
            "apikey":     self.api_key,
            "format":     "JSON",
            "order":      "ASC",
            "outputsize": min(limit, 5000),
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(f"{self.base_url}/time_series", params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "error":
                    logger.warning(f"Twelve Data error for {symbol}: {data.get('message')}")
                    return []

                if "values" not in data:
                    return []

                result = []
                for candle in data["values"]:
                    try:
                        result.append(OHLCVData(
                            symbol=symbol,
                            timeframe=timeframe,
                            open=float(candle["open"]),
                            high=float(candle["high"]),
                            low=float(candle["low"]),
                            close=float(candle["close"]),
                            volume=float(candle.get("volume", 0)),
                            timestamp=datetime.fromisoformat(
                                candle["datetime"].replace("Z", "+00:00")
                            ),
                            data_source="twelve_data",
                        ))
                    except (ValueError, KeyError) as e:
                        logger.debug(f"Skipping malformed candle for {symbol}: {e}")
                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"Twelve Data HTTP {e.response.status_code} for {symbol}")
                return []
            except httpx.RequestError as e:
                logger.error(f"Twelve Data request error for {symbol}: {e}")
                return []

    async def fetch_latest_tick(self, symbol: str) -> TickData:
        td_symbol = self._resolve_symbol(symbol)
        params = {"symbol": td_symbol, "apikey": self.api_key, "format": "JSON"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.base_url}/quote", params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "error":
                raise ValueError(f"Twelve Data error: {data.get('message')}")

            last = float(data.get("close", data.get("last", 0)))
            bid = float(data.get("bid", last))
            ask = float(data.get("ask", last))

            # Twelve Data quote timestamp can be epoch or ISO string
            raw_ts = data.get("timestamp", "")
            try:
                ts = (
                    datetime.fromtimestamp(int(raw_ts), tz=UTC)
                    if str(raw_ts).isdigit()
                    else datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                )
            except (ValueError, TypeError):
                ts = datetime.now(UTC)

            return TickData(
                symbol=symbol,
                bid=bid,
                ask=ask,
                price=round((bid + ask) / 2, 8),
                volume=float(data.get("volume", 0)),
                timestamp=ts,
                data_source="twelve_data",
            )

    async def get_available_symbols(self) -> List[str]:
        return TRACKED_SYMBOLS

    async def validate_connection(self) -> bool:
        try:
            tick = await self.fetch_latest_tick("XAUUSD")
            return tick.price > 0
        except Exception as e:
            logger.error(f"Twelve Data connection failed: {e}")
            return False
