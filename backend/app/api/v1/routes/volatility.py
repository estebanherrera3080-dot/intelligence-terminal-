"""
Volatility Engine — REST endpoints.

GET /api/v1/volatility/analysis   Full volatility analysis for a symbol
GET /api/v1/volatility/summary    Multi-symbol summary (dashboard)
GET /api/v1/volatility/regime     Regime + score only (lightweight)
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.logger import get_logger
from app.services.market_data.providers import get_active_provider
from app.services.market_data.providers.base import BaseMarketDataProvider
from app.services.volatility.engine import VolatilityEngine

logger = get_logger(__name__)
router = APIRouter(prefix="/volatility", tags=["volatility"])


def _provider() -> BaseMarketDataProvider:
    return get_active_provider()


def get_engine(provider: BaseMarketDataProvider = Depends(_provider)) -> VolatilityEngine:
    return VolatilityEngine(provider=provider)


@router.get("/analysis")
async def get_analysis(
    symbol:    str = Query("XAUUSD"),
    timeframe: str = Query("1h"),
    limit:     int = Query(60, ge=15, le=500),
    engine: VolatilityEngine = Depends(get_engine),
):
    """Full volatility analysis: ATR, realized vol, range, regime."""
    try:
        return (await engine.analyze(symbol=symbol, timeframe=timeframe, limit=limit)).model_dump()
    except Exception as e:
        logger.error(f"Volatility analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary(engine: VolatilityEngine = Depends(get_engine)):
    """Multi-symbol volatility summary for dashboard."""
    try:
        return (await engine.analyze_all()).model_dump()
    except Exception as e:
        logger.error(f"Volatility summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime")
async def get_regime(
    symbol:    str = Query("XAUUSD"),
    timeframe: str = Query("1h"),
    engine: VolatilityEngine = Depends(get_engine),
):
    """Lightweight regime endpoint for dashboard header."""
    try:
        r = await engine.analyze(symbol=symbol, timeframe=timeframe)
        return {
            "symbol":            r.symbol,
            "regime":            r.regime,
            "regime_score":      r.regime_score,
            "compression_score": r.compression_score,
            "expansion_score":   r.expansion_score,
            "atr_pct":           r.atr_pct,
            "atr_zscore":        r.atr_zscore,
            "realized_vol_20":   r.realized_vol_20,
            "signals":           r.signals,
            "timestamp":         r.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
