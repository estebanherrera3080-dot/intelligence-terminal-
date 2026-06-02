"""
Gold Intelligence Engine — multi-timeframe bias schemas.
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class HorizonBias(BaseModel):
    """
    Conviction score for a single timeframe.
    Synthesizes momentum, SMC structure, volatility, and macro alignment.
    """
    horizon:          str   = Field(..., description="5m | 15m | 1h | macro")
    timeframe_label:  str   = Field(..., description="Display label")
    conviction_score: int   = Field(..., ge=0, le=100,
                                    description="0=max bearish, 50=neutral, 100=max bullish")
    bias:             str   = Field(..., description="bullish | neutral | bearish")
    confidence:       float = Field(..., ge=0, le=100, description="%")
    regime:           str   = Field(..., description="Dominant regime for this TF")
    drivers:          List[str] = Field(default_factory=list, description="Top 3 signal drivers")

    # Component breakdown
    momentum_score:   int   = Field(0, ge=0, le=100)
    structure_score:  int   = Field(0, ge=0, le=100)
    volatility_score: int   = Field(0, ge=0, le=100)
    macro_alignment:  int   = Field(0, ge=0, le=100,
                                    description="Degree to which macro context supports this TF bias")


class ConsensusResult(BaseModel):
    """
    Multi-timeframe Gold Intelligence consensus.

    Weights (institutional design):
      5m    → 10%  (noise-heavy, used only for entry timing)
      15m   → 20%  (microstructure, SMC setups)
      1h    → 35%  (primary trading timeframe for gold)
      macro → 35%  (dominant driver for a macro asset like gold)

    Alignment:
      aligned   → all 4 biases agree
      mixed     → 3 of 4 agree
      conflicted → ≤2 agree (confidence penalized)
    """
    timestamp:   datetime

    m5:    HorizonBias
    m15:   HorizonBias
    h1:    HorizonBias
    macro: HorizonBias

    # Consensus
    consensus_score: int   = Field(..., ge=0, le=100)
    consensus_bias:  str   = Field(..., description="bullish | neutral | bearish")
    alignment:       str   = Field(..., description="aligned | mixed | conflicted")
    confidence:      float = Field(..., ge=0, le=100)

    # Narrative
    dominant_timeframe: str = Field(..., description="TF with highest conviction")
    key_insight:        str = ""
