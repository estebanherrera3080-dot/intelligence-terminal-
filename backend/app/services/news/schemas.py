"""
Institutional News Engine — output schemas.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NewsEvent(BaseModel):
    """A single classified news event."""
    id:           str
    title:        str
    event_type:   str   = Field(..., description=(
        "FOMC | POWELL | FED_SPEAKER | CPI | PCE | NFP | "
        "TREASURY | GDP | RETAIL_SALES | ISM | OTHER"
    ))
    timestamp:    datetime
    sentiment:    str   = Field(..., description="hawkish | neutral | dovish")
    impact_score: int   = Field(..., ge=0, le=100,
                                description="Market impact 0-100")
    gold_impact:  str   = Field(..., description="bullish | neutral | bearish")
    confidence:   float = Field(..., ge=0, le=100)
    summary:      str   = ""
    raw_text:     Optional[str] = None
    source:       str   = "calendar"


class EconomicCalendarEntry(BaseModel):
    """Scheduled economic release."""
    event_type:  str
    title:       str
    scheduled:   datetime
    actual:      Optional[float] = None
    forecast:    Optional[float] = None
    previous:    Optional[float] = None
    surprise_pct: Optional[float] = None   # (actual - forecast) / |forecast| * 100
    released:    bool = False


class NewsAnalysis(BaseModel):
    """Aggregated news analysis output."""
    timestamp:     datetime

    # Recent high-impact events
    events:        List[NewsEvent] = Field(default_factory=list)

    # Aggregate Fed stance from recent events
    fed_stance:    str   = Field(..., description="hawkish | neutral | dovish")
    fed_score:     int   = Field(..., ge=0, le=100,
                                  description="0=max dovish, 50=neutral, 100=max hawkish")
    fed_confidence: float = Field(..., ge=0, le=100)

    # Gold news bias
    news_gold_bias:   str   = Field(..., description="bullish | neutral | bearish")
    news_impact_score: int  = Field(..., ge=0, le=100,
                                    description="Aggregate news pressure on gold 0-100")

    # Calendar
    upcoming_events:  List[EconomicCalendarEntry] = Field(default_factory=list)
    last_major_event: Optional[str] = None

    # Narrative
    key_headlines:    List[str] = Field(default_factory=list)
    risk_events:      List[str] = Field(default_factory=list)
