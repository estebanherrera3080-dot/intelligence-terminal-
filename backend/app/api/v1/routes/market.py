"""
Market data REST routes.

Tick endpoints (/latest, /latest/all):
  - Read exclusively from TickStore (Redis → memory fallback).
  - Never call the provider directly.
  - On cold cache (first startup before Celery runs): transparently
    falls back to one direct provider fetch and populates the cache,
    so the dashboard is live without waiting for Celery.

OHLCV endpoint (/ohlcv):
  - Tries TickStore (Redis) first.
  - Falls back to MarketDataService → PostgreSQL → provider.
  - Result is written back to TickStore to warm future requests.

Other endpoints (/symbols, /health, /refresh) are unchanged.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.db.session import get_db
from app.schemas.market import LatestTickResponse, OHLCVResponse, OHLCVData
from app.services.cache.tick_store import tick_store
from app.services.market_data.providers import get_active_provider
from app.services.market_data.providers.base import BaseMarketDataProvider
from app.services.market_data.service import TRACKED_SYMBOLS, MarketDataService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/market",
    tags=["market"],
    responses={404: {"description": "Not found"}},
)


# ── Shared dependency: MarketDataService ─────────────────────────── #

def _provider() -> BaseMarketDataProvider:
    return get_active_provider()


async def get_service(
    db: AsyncSession = Depends(get_db),
    provider: BaseMarketDataProvider = Depends(_provider),
) -> MarketDataService:
    return MarketDataService(provider=provider, db=db)


# ── Helpers ──────────────────────────────────────────────────────── #

def _validate_symbol(symbol: str) -> None:
    if symbol.upper() not in TRACKED_SYMBOLS:
        logger.warning(f"Request for untracked symbol: {symbol}")


async def _provider_tick_to_payload(provider: BaseMarketDataProvider, symbol: str) -> dict:
    """Fetch one tick from provider and return as cache-compatible dict."""
    tick = await provider.fetch_latest_tick(symbol)
    return {
        "price":     tick.price,
        "bid":       tick.bid,
        "ask":       tick.ask,
        "spread":    round(tick.ask - tick.bid, 8),
        "volume":    tick.volume,
        "timestamp": tick.timestamp.isoformat(),
        "source":    tick.data_source,
    }


# ── GET /latest/all ──────────────────────────────────────────────── #

@router.get("/latest/all")
async def get_all_latest_ticks(
    provider: BaseMarketDataProvider = Depends(_provider),
):
    """
    Latest tick for every tracked symbol.
    Primary source: TickStore (Redis/memory) — zero provider API calls.
    Fallback: direct provider fetch when cache is completely cold,
              result is written to cache for subsequent requests.
    """
    snapshot = await tick_store.get_snapshot()
    if snapshot:
        return snapshot

    # Cache cold (Celery not running yet) — fetch once and warm cache.
    logger.warning(
        "Tick snapshot cache is cold — fetching from provider. "
        "Start Celery Beat to eliminate these direct provider calls."
    )
    fresh: dict = {}
    for symbol in TRACKED_SYMBOLS:
        try:
            payload = await _provider_tick_to_payload(provider, symbol)
            await tick_store.set_tick(symbol, payload)
            fresh[symbol] = payload
        except Exception as exc:
            logger.error(f"Cold-cache fetch failed for {symbol}: {exc}")

    if fresh:
        await tick_store.set_snapshot(fresh)

    if not fresh:
        raise HTTPException(
            status_code=503,
            detail="Market data unavailable: cache cold and provider unreachable.",
        )
    return fresh


# ── GET /latest ──────────────────────────────────────────────────── #

@router.get("/latest", response_model=LatestTickResponse)
async def get_latest_tick(
    symbol: str = Query(..., description="Symbol (e.g. XAUUSD)"),
    provider: BaseMarketDataProvider = Depends(_provider),
):
    """
    Latest tick for a single symbol.
    Primary source: TickStore. Fallback: direct provider fetch on cache miss.
    """
    _validate_symbol(symbol)
    sym = symbol.upper()

    data = await tick_store.get_tick(sym)
    if not data:
        logger.warning(f"Cache miss for {sym} — fetching from provider (cold cache)")
        try:
            data = await _provider_tick_to_payload(provider, sym)
            await tick_store.set_tick(sym, data)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"No data for {sym}: {exc}")

    return LatestTickResponse(
        symbol=sym,
        bid=data["bid"],
        ask=data["ask"],
        price=data["price"],
        spread=data["spread"],
        volume=data["volume"],
        timestamp=data["timestamp"],
    )


# ── GET /ohlcv ───────────────────────────────────────────────────── #

@router.get("/ohlcv", response_model=OHLCVResponse)
async def get_ohlcv(
    symbol: str = Query(..., description="Symbol (e.g. XAUUSD)"),
    timeframe: str = Query("1h", description="Timeframe: 1m 5m 15m 1h 4h 1d"),
    limit: int = Query(200, ge=1, le=5000),
    service: MarketDataService = Depends(get_service),
):
    """
    OHLCV candlestick data.
    Read order: Redis cache → PostgreSQL → provider.
    Writes result back to Redis so next request is served from cache.
    """
    _validate_symbol(symbol)
    sym = symbol.upper()

    # 1. Try Redis cache first
    cached = await tick_store.get_ohlcv(sym, timeframe)
    if cached and len(cached) >= min(limit, 3):
        candles = cached[-limit:]
        return OHLCVResponse(symbol=sym, timeframe=timeframe, count=len(candles), data=candles)

    # 2. Fall back to MarketDataService (PostgreSQL → provider)
    try:
        data = await service.get_ohlcv(symbol=sym, timeframe=timeframe, limit=limit)
    except Exception as exc:
        logger.error(f"OHLCV error {sym}/{timeframe}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    if not data:
        raise HTTPException(status_code=404, detail=f"No OHLCV data for {sym}/{timeframe}")

    # 3. Populate Redis cache with the result
    candles_json = [
        {
            "symbol":      c.symbol,
            "timeframe":   c.timeframe,
            "open":        c.open,
            "high":        c.high,
            "low":         c.low,
            "close":       c.close,
            "volume":      c.volume,
            "timestamp":   c.timestamp.isoformat() if hasattr(c.timestamp, "isoformat") else c.timestamp,
            "data_source": c.data_source,
        }
        for c in data
    ]
    await tick_store.set_ohlcv(sym, timeframe, candles_json)

    return OHLCVResponse(symbol=sym, timeframe=timeframe, count=len(data), data=data)


# ── GET /symbols ─────────────────────────────────────────────────── #

@router.get("/symbols")
async def get_symbols(service: MarketDataService = Depends(get_service)):
    """Available symbols from the active provider."""
    try:
        symbols = await service.get_available_symbols()
        return {"symbols": symbols, "count": len(symbols)}
    except Exception as exc:
        logger.error(f"Symbols error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /health ──────────────────────────────────────────────────── #

@router.get("/health")
async def market_health(service: MarketDataService = Depends(get_service)):
    """
    Market data service health.
    Includes provider connectivity and cache layer status.
    """
    try:
        provider_health = await service.health_check()
        cache_status = await tick_store.status()
        return {**provider_health, "cache": cache_status}
    except Exception as exc:
        logger.error(f"Health check error: {exc}")
        return {"status": "unhealthy", "error": str(exc)}


# ── POST /refresh/{symbol} ───────────────────────────────────────── #

@router.post("/refresh/{symbol}")
async def refresh_symbol(
    symbol: str,
    timeframe: str = Query("1h"),
    limit: int = Query(500, ge=1, le=5000),
    service: MarketDataService = Depends(get_service),
):
    """
    Force-fetch from provider and store in DB + Redis cache.
    Use this to warm the cache after deploying or adding a new symbol.
    """
    try:
        data = await service.refresh_symbol(symbol=symbol, timeframe=timeframe, limit=limit)
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
                    "timestamp":   c.timestamp.isoformat() if hasattr(c.timestamp, "isoformat") else c.timestamp,
                    "data_source": c.data_source,
                }
                for c in data
            ]
            await tick_store.set_ohlcv(symbol.upper(), timeframe, candles_json)
        return {"symbol": symbol, "timeframe": timeframe, "stored": len(data)}
    except Exception as exc:
        logger.error(f"Refresh error {symbol}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
