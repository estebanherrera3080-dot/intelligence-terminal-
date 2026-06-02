"""
Smart Money Concepts — REST endpoints.

GET /api/v1/smc/analysis          Full SMC analysis for a symbol/timeframe
GET /api/v1/smc/events            Latest events only
GET /api/v1/smc/zones             FVG zones + Order Blocks only
GET /api/v1/smc/bias              Structure bias summary (lightweight)
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.logger import get_logger
from app.services.market_data.providers import get_active_provider
from app.services.market_data.providers.base import BaseMarketDataProvider
from app.services.smc.engine import SmartMoneyEngine

logger = get_logger(__name__)
router = APIRouter(prefix="/smc", tags=["smc"])


def _provider() -> BaseMarketDataProvider:
    return get_active_provider()


def get_engine(provider: BaseMarketDataProvider = Depends(_provider)) -> SmartMoneyEngine:
    return SmartMoneyEngine(provider=provider)


@router.get("/analysis")
async def get_analysis(
    symbol:    str = Query("XAUUSD", description="Symbol to analyse"),
    timeframe: str = Query("1h",     description="1h | 4h | 1d"),
    limit:     int = Query(100, ge=20, le=500, description="Candles to scan"),
    engine: SmartMoneyEngine = Depends(get_engine),
):
    """Full SMC analysis: BOS, CHoCH, FVG, Order Blocks, Liquidity."""
    try:
        r = await engine.analyze(symbol=symbol, timeframe=timeframe, limit=limit)
        return r.model_dump()
    except Exception as e:
        logger.error(f"SMC analysis error {symbol}/{timeframe}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bias")
async def get_bias(
    symbol:    str = Query("XAUUSD"),
    timeframe: str = Query("1h"),
    engine: SmartMoneyEngine = Depends(get_engine),
):
    """Structure bias summary — lightweight for dashboard header."""
    try:
        r = await engine.analyze(symbol=symbol, timeframe=timeframe, limit=60)
        return {
            "symbol":          r.symbol,
            "timeframe":       r.timeframe,
            "structure_bias":  r.structure_bias,
            "bias_strength":   round(r.bias_strength, 1),
            "last_bos":        r.last_bos,
            "last_choch":      r.last_choch,
            "event_count":     len(r.events),
            "nearest_fvg_above": r.nearest_fvg_above,
            "nearest_fvg_below": r.nearest_fvg_below,
            "nearest_ob_above":  r.nearest_ob_above,
            "nearest_ob_below":  r.nearest_ob_below,
            "timestamp":       r.timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"SMC bias error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_events(
    symbol:    str = Query("XAUUSD"),
    timeframe: str = Query("1h"),
    limit:     int = Query(100),
    engine: SmartMoneyEngine = Depends(get_engine),
):
    """Latest SMC events (BOS, CHoCH, Sweeps) in chronological order."""
    try:
        r = await engine.analyze(symbol=symbol, timeframe=timeframe, limit=limit)
        return {
            "symbol": r.symbol, "timeframe": r.timeframe,
            "events": [e.model_dump() for e in r.events],
            "count":  len(r.events),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zones")
async def get_zones(
    symbol:    str = Query("XAUUSD"),
    timeframe: str = Query("1h"),
    engine: SmartMoneyEngine = Depends(get_engine),
):
    """FVG zones and Order Blocks."""
    try:
        r = await engine.analyze(symbol=symbol, timeframe=timeframe, limit=100)
        return {
            "symbol": r.symbol, "timeframe": r.timeframe,
            "fvg_zones":    [z.model_dump() for z in r.fvg_zones],
            "order_blocks": [b.model_dump() for b in r.order_blocks],
            "liquidity_levels": [l.model_dump() for l in r.liquidity_levels],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
