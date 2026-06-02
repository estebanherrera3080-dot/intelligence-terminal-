"""
News Engine — REST endpoints.

GET  /api/v1/news/analysis      Full news analysis + Fed stance
GET  /api/v1/news/fed           Fed stance summary (lightweight)
GET  /api/v1/news/events        Recent classified events
GET  /api/v1/news/calendar      Upcoming economic releases
POST /api/v1/news/classify      Ad-hoc text classification
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.logger import get_logger
from app.services.news.engine import NewsEngine

logger = get_logger(__name__)
router = APIRouter(prefix="/news", tags=["news"])


def get_engine() -> NewsEngine:
    return NewsEngine()


@router.get("/analysis")
async def get_analysis(engine: NewsEngine = Depends(get_engine)):
    """Full news analysis: Fed stance, gold bias, all events."""
    try:
        r = await engine.analyze()
        return r.model_dump()
    except Exception as e:
        logger.error(f"News analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fed")
async def get_fed_stance(engine: NewsEngine = Depends(get_engine)):
    """Fed stance summary — lightweight for dashboard."""
    try:
        r = await engine.analyze()
        return {
            "fed_stance":       r.fed_stance,
            "fed_score":        r.fed_score,
            "fed_confidence":   r.fed_confidence,
            "news_gold_bias":   r.news_gold_bias,
            "news_impact_score": r.news_impact_score,
            "last_major_event": r.last_major_event,
            "risk_event_count": len(r.risk_events),
            "timestamp":        r.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_events(engine: NewsEngine = Depends(get_engine)):
    """Recent classified news events."""
    try:
        r = await engine.analyze()
        return {
            "events": [e.model_dump() for e in r.events],
            "count":  len(r.events),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar")
async def get_calendar(engine: NewsEngine = Depends(get_engine)):
    """Upcoming economic calendar releases."""
    try:
        r = await engine.analyze()
        return {
            "upcoming": [c.model_dump() for c in r.upcoming_events],
            "count":    len(r.upcoming_events),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ClassifyRequest(BaseModel):
    text: str
    event_type: str = "OTHER"


@router.post("/classify")
async def classify_text(
    req: ClassifyRequest,
    engine: NewsEngine = Depends(get_engine),
):
    """
    Ad-hoc text classification — paste any Fed statement, speech, or headline.
    Returns sentiment + impact score + gold bias.
    """
    try:
        return await engine.classify_text(req.text, req.event_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
