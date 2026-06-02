"""
MacroTrend Engine — REST endpoints.

GET /api/v1/macro/analysis    Full macro analysis
GET /api/v1/macro/snapshot    Raw macro data snapshot only
GET /api/v1/macro/regime      Regime classifications only (lightweight)
GET /api/v1/macro/scores      Scores + bias only
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.logger import get_logger
from app.services.macro.engine import MacroTrendEngine
from app.services.market_data.providers import get_active_provider
from app.services.market_data.providers.base import BaseMarketDataProvider

logger = get_logger(__name__)

router = APIRouter(prefix="/macro", tags=["macro"])


def _provider() -> BaseMarketDataProvider:
    return get_active_provider()


def get_engine(
    provider: BaseMarketDataProvider = Depends(_provider),
) -> MacroTrendEngine:
    return MacroTrendEngine(provider=provider)


# ─────────────────────────────────────────────────────────────────


@router.get("/analysis")
async def get_full_analysis(engine: MacroTrendEngine = Depends(get_engine)):
    """
    Full MacroTrend analysis.
    Returns macro_score, risk_score, gold_bias, confidence,
    all regime classifications, component scores, and narrative.
    """
    try:
        result = await engine.analyze()
        return result.model_dump()
    except Exception as e:
        logger.error(f"Macro analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scores")
async def get_scores(engine: MacroTrendEngine = Depends(get_engine)):
    """Lightweight endpoint — scores + bias only. Suitable for dashboard headers."""
    try:
        r = await engine.analyze()
        return {
            "macro_score":  r.macro_score,
            "risk_score":   r.risk_score,
            "gold_bias":    r.gold_bias,
            "confidence":   r.confidence,
            "market_regime": r.market_regime,
            "macro_regime":  r.macro_regime,
            "timestamp":    r.timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"Macro scores error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime")
async def get_regime(engine: MacroTrendEngine = Depends(get_engine)):
    """Regime classifications + liquidity conditions."""
    try:
        r = await engine.analyze()
        return {
            "market_regime":       r.market_regime,
            "macro_regime":        r.macro_regime,
            "liquidity_conditions": r.liquidity_conditions,
            "gold_bias":           r.gold_bias,
            "key_signals":         r.key_signals,
            "risk_factors":        r.risk_factors,
            "timestamp":           r.timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"Macro regime error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot")
async def get_snapshot(engine: MacroTrendEngine = Depends(get_engine)):
    """Raw market data snapshot used by the macro engine."""
    try:
        r = await engine.analyze()
        return r.snapshot.model_dump()
    except Exception as e:
        logger.error(f"Macro snapshot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
