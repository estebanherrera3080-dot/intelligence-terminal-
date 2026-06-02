"""
Correlation Engine — REST endpoints.

GET /api/v1/correlation/analysis     Full correlation matrix + breakdowns
GET /api/v1/correlation/gold         Gold correlation profile only
GET /api/v1/correlation/breakdowns   Active breakdown events
GET /api/v1/correlation/regime       Regime + dominant signal (lightweight)
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.logger import get_logger
from app.services.correlation.engine import CorrelationEngine
from app.services.market_data.providers import get_active_provider
from app.services.market_data.providers.base import BaseMarketDataProvider

logger = get_logger(__name__)
router = APIRouter(prefix="/correlation", tags=["correlation"])


def _provider() -> BaseMarketDataProvider:
    return get_active_provider()


def get_engine(provider: BaseMarketDataProvider = Depends(_provider)) -> CorrelationEngine:
    return CorrelationEngine(provider=provider)


@router.get("/analysis")
async def get_analysis(
    limit: int = Query(80, ge=25, le=500),
    engine: CorrelationEngine = Depends(get_engine),
):
    """Full correlation matrix with breakdown detection."""
    try:
        r = await engine.analyze(limit=limit)
        return r.model_dump()
    except Exception as e:
        logger.error(f"Correlation analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gold")
async def get_gold_profile(engine: CorrelationEngine = Depends(get_engine)):
    """Gold correlation profile — current vs expected vs deviation."""
    try:
        r = await engine.analyze()
        return r.gold_profile.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/breakdowns")
async def get_breakdowns(engine: CorrelationEngine = Depends(get_engine)):
    """Active correlation breakdown events."""
    try:
        r = await engine.analyze()
        return {
            "breakdowns": [b.model_dump() for b in r.breakdown_events],
            "count":       len(r.breakdown_events),
            "regime":      r.regime,
            "timestamp":   r.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime")
async def get_regime(engine: CorrelationEngine = Depends(get_engine)):
    """Lightweight regime endpoint for dashboard."""
    try:
        r = await engine.analyze()
        return {
            "regime":         r.regime,
            "regime_score":   r.regime_score,
            "dominant_signal": r.dominant_signal,
            "breakdown_count": len(r.breakdown_events),
            "gold_vs_dxy":    r.gold_profile.xauusd_vs.get("DXY"),
            "gold_vs_vix":    r.gold_profile.xauusd_vs.get("VIX"),
            "gold_vs_spx":    r.gold_profile.xauusd_vs.get("SPX"),
            "gold_vs_us10y":  r.gold_profile.xauusd_vs.get("US10Y"),
            "timestamp":      r.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
