"""
Correlation Engine — output schemas.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PairCorrelation(BaseModel):
    symbol_a:      str
    symbol_b:      str
    pair:          str   # "XAUUSD-DXY"

    # Current vs historical
    corr_current:  float = Field(..., ge=-1, le=1, description="20-period Pearson")
    corr_50:       float = Field(..., ge=-1, le=1, description="50-period Pearson (historical norm)")
    corr_delta:    float = Field(..., description="corr_current - corr_50 (deviation)")
    zscore:        float = Field(..., description="Deviation in standard deviations")

    # Classification
    direction:     str   = Field(..., description="positive | negative | neutral")
    strength:      str   = Field(..., description="strong | moderate | weak | none")
    is_breakdown:  bool  = False

    # Human label
    interpretation: str  = ""


class BreakdownEvent(BaseModel):
    pair:             str
    timestamp:        datetime
    normal_corr:      float
    current_corr:     float
    deviation:        float
    zscore:           float
    severity:         str   # minor | moderate | major
    description:      str


class GoldCorrelationProfile(BaseModel):
    """Gold's correlation with each tracked instrument."""
    timestamp:   datetime
    xauusd_vs:   Dict[str, float]   # symbol → current correlation with gold
    # Canonical expected correlations (institutional knowledge)
    expected:    Dict[str, float]   # symbol → typical historical correlation
    deviations:  Dict[str, float]   # symbol → current vs expected delta


class CorrelationAnalysis(BaseModel):
    """Full correlation analysis output."""
    timestamp:        datetime
    pairs:            List[PairCorrelation]
    breakdown_events: List[BreakdownEvent]
    gold_profile:     GoldCorrelationProfile

    # Overall regime
    regime:           str   # normal | stressed | breakdown
    regime_score:     float  # 0-100, higher = more broken down
    dominant_signal:  str   = ""  # narrative summary of most important correlation

    candles_used:     int   = 0
