"""
Provider factory — selects the active data provider based on configured API keys.
"""

from app.core.config import settings
from app.services.market_data.providers.base import BaseMarketDataProvider


def get_active_provider() -> BaseMarketDataProvider:
    """
    Return the best available provider:
    1. Twelve Data  — when TWELVE_DATA_API_KEY is set
    2. Mock         — development / CI fallback
    """
    if settings.twelve_data_api_key:
        from app.services.market_data.providers.twelve_data import TwelveDataProvider
        return TwelveDataProvider(api_key=settings.twelve_data_api_key)

    from app.services.market_data.providers.mock import MockMarketDataProvider
    return MockMarketDataProvider()


__all__ = ["BaseMarketDataProvider", "get_active_provider"]
