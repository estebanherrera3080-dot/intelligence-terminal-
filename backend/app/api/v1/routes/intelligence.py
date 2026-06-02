"""
Gold Intelligence Engine — REST endpoints.

GET /api/v1/intelligence/consensus   Full multi-TF consensus
GET /api/v1/intelligence/bias        Scores + bias per TF (dashboard)
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.logger import get_logger
from app.services.gold_intelligence.engine import GoldIntelligenceEngine
from app.services.market_data.providers import get_active_provider
from app.services.market_data.providers.base import BaseMarketDataProvider

logger = get_logger(__name__)
router = APIRouter(prefix="/intelligence", tags=["intelligence"])


def _provider() -> BaseMarketDataProvider:
    return get_active_provider()


def get_engine(provider: BaseMarketDataProvider = Depends(_provider)) -> GoldIntelligenceEngine:
    return GoldIntelligenceEngine(provider=provider)


@router.get("/consensus")
async def get_consensus(engine: GoldIntelligenceEngine = Depends(get_engine)):
    """Full multi-timeframe Gold Intelligence consensus."""
    try:
        r = await engine.analyze()
        return r.model_dump()
    except Exception as e:
        logger.error(f"Intelligence consensus error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bias")
async def get_bias(engine: GoldIntelligenceEngine = Depends(get_engine)):
    """Per-timeframe conviction scores — optimised for dashboard rendering."""
    try:
        r = await engine.analyze()
        return {
            "consensus_score": r.consensus_score,
            "consensus_bias":  r.consensus_bias,
            "alignment":       r.alignment,
            "confidence":      r.confidence,
            "dominant_timeframe": r.dominant_timeframe,
            "key_insight":     r.key_insight,
            "timeframes": {
                "5m":    _horizon_summary(r.m5),
                "15m":   _horizon_summary(r.m15),
                "1h":    _horizon_summary(r.h1),
                "macro": _horizon_summary(r.macro),
            },
            "timestamp": r.timestamp.isoformat(),
        }
    except Exception as e:
        logger.error(f"Intelligence bias error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _horizon_summary(h) -> dict:
    return {
        "conviction_score": h.conviction_score,
        "bias":             h.bias,
        "confidence":       h.confidence,
        "regime":           h.regime,
        "drivers":          h.drivers,
        "momentum_score":   h.momentum_score,
        "structure_score":  h.structure_score,
        "macro_alignment":  h.macro_alignment,
    }
