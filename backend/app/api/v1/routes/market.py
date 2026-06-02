"""
Market data REST routes.
All data access goes through MarketDataService, which handles
provider selection, DB caching, and persistence.

GET /api/v1/market/ohlcv
GET /api/v1/market/latest
GET /api/v1/market/latest/all
GET /api/v1/market/symbols
GET /api/v1/market/health
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.db.session import get_db
from app.schemas.market import LatestTickResponse, OHLCVResponse
from app.services.market_data.providers import get_active_provider
from app.services.market_data.providers.base import BaseMarketDataProvider
from app.services.market_data.service import TRACKED_SYMBOLS, MarketDataService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/market",
    tags=["market"],
    responses={404: {"description": "Not found"}},
)


# ------------------------------------------------------------------ #
#  Dependencies                                                        #
# ------------------------------------------------------------------ #

def _provider() -> BaseMarketDataProvider:
    return get_active_provider()


async def get_service(
    db: AsyncSession = Depends(get_db),
    provider: BaseMarketDataProvider = Depends(_provider),
) -> MarketDataService:
    return MarketDataService(provider=provider, db=db)


# ------------------------------------------------------------------ #
#  Endpoints                                                           #
# ------------------------------------------------------------------ #

def _validate_symbol(symbol: str) -> None:
    """Warn (not error) for unknown symbols — provider may still serve them."""
    if symbol.upper() not in TRACKED_SYMBOLS:
        logger.warning(f"Request for untracked symbol: {symbol} (not in {TRACKED_SYMBOLS})")


@router.get("/ohlcv", response_model=OHLCVResponse)
async def get_ohlcv(
    symbol: str = Query(..., description="Symbol (e.g. XAUUSD, DXY, VIX)"),
    timeframe: str = Query("1h", description="Timeframe: 1m 5m 15m 30m 1h 4h 1d"),
    limit: int = Query(200, ge=1, le=5000, description="Number of candles"),
    service: MarketDataService = Depends(get_service),
):
    """
    OHLCV candlestick data.
    Returns cached data from DB when available; fetches from provider on cache miss.
    """
    try:
        _validate_symbol(symbol)
        data = await service.get_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
        if not data:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        return OHLCVResponse(symbol=symbol, timeframe=timeframe, count=len(data), data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OHLCV error {symbol}/{timeframe}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest", response_model=LatestTickResponse)
async def get_latest_tick(
    symbol: str = Query(..., description="Symbol (e.g. XAUUSD)"),
    service: MarketDataService = Depends(get_service),
):
    """Latest bid/ask/price tick for a symbol. Always fetches live from provider."""
    try:
        _validate_symbol(symbol)
        tick = await service.get_latest_tick(symbol)
        return LatestTickResponse(
            symbol=symbol,
            bid=tick.bid,
            ask=tick.ask,
            price=tick.price,
            spread=round(tick.ask - tick.bid, 8),
            volume=tick.volume,
            timestamp=tick.timestamp,
        )
    except Exception as e:
        logger.error(f"Latest tick error {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest/all")
async def get_all_latest_ticks(service: MarketDataService = Depends(get_service)):
    """
    Latest tick for every tracked symbol in one call.
    Used by the Executive Dashboard to populate the watchlist.
    """
    try:
        return await service.get_latest_ticks_all()
    except Exception as e:
        logger.error(f"All ticks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols")
async def get_symbols(service: MarketDataService = Depends(get_service)):
    """Available symbols from the active provider."""
    try:
        symbols = await service.get_available_symbols()
        return {"symbols": symbols, "count": len(symbols)}
    except Exception as e:
        logger.error(f"Symbols error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh/{symbol}")
async def refresh_symbol(
    symbol: str,
    timeframe: str = Query("1h"),
    limit: int = Query(500, ge=1, le=5000),
    service: MarketDataService = Depends(get_service),
):
    """
    Force-fetch and store data from provider for a specific symbol.
    Use this to warm the cache after deploying or adding a new symbol.
    """
    try:
        data = await service.refresh_symbol(symbol=symbol, timeframe=timeframe, limit=limit)
        return {"symbol": symbol, "timeframe": timeframe, "stored": len(data)}
    except Exception as e:
        logger.error(f"Refresh error {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def market_health(service: MarketDataService = Depends(get_service)):
    """Market data service health — includes provider connectivity."""
    try:
        return await service.health_check()
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {"status": "unhealthy", "error": str(e)}
