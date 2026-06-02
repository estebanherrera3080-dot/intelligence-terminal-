"""
Smart Money Concepts — output schemas.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SMCEvent(BaseModel):
    """A single detected SMC event on a specific candle."""

    event_type: str = Field(..., description=(
        "BOS_BULLISH | BOS_BEARISH | CHOCH_BULLISH | CHOCH_BEARISH | "
        "FVG_BULLISH | FVG_BEARISH | ORDER_BLOCK_BULLISH | ORDER_BLOCK_BEARISH | "
        "EQUAL_HIGHS | EQUAL_LOWS | LIQUIDITY_SWEEP_HIGH | LIQUIDITY_SWEEP_LOW"
    ))
    timestamp: datetime
    price:      float = Field(..., description="Reference price level of the event")
    high:       Optional[float] = None
    low:        Optional[float] = None
    intensity:  float = Field(..., ge=0, le=100, description="Signal strength 0-100")
    probability: float = Field(..., ge=0, le=100, description="Follow-through probability 0-100")
    timeframe:  str
    symbol:     str
    description: str = ""


class FVGZone(BaseModel):
    """Fair Value Gap — an imbalance between candles that may act as magnet."""
    direction:    str    # bullish | bearish
    top:          float
    bottom:       float
    midpoint:     float
    gap_size:     float
    gap_pct:      float  # gap as % of price
    timestamp:    datetime
    filled:       bool = False
    intensity:    float


class OrderBlock(BaseModel):
    """Order Block — institutional candle before a strong move."""
    direction:   str    # bullish | bearish
    top:         float
    bottom:      float
    midpoint:    float
    timestamp:   datetime
    strength:    float   # 0-100, based on subsequent move size
    tested:      bool = False


class LiquidityLevel(BaseModel):
    """Equal highs/lows cluster = pool of resting orders."""
    level_type:  str    # equal_highs | equal_lows
    price:       float
    touches:     int
    timestamp:   datetime
    swept:       bool = False
    intensity:   float


class SMCAnalysis(BaseModel):
    """Full Smart Money Concepts analysis result."""
    symbol:    str
    timeframe: str
    timestamp: datetime

    # Detected events (chronological)
    events:     List[SMCEvent]    = Field(default_factory=list)
    fvg_zones:  List[FVGZone]    = Field(default_factory=list)
    order_blocks: List[OrderBlock] = Field(default_factory=list)
    liquidity_levels: List[LiquidityLevel] = Field(default_factory=list)

    # Aggregated bias from SMC structure
    structure_bias:  str   = "neutral"   # bullish | neutral | bearish
    bias_strength:   float = 0.0         # 0-100
    last_bos:        Optional[str] = None  # bullish | bearish
    last_choch:      Optional[str] = None

    # Key levels
    nearest_fvg_above: Optional[float] = None
    nearest_fvg_below: Optional[float] = None
    nearest_ob_above:  Optional[float] = None
    nearest_ob_below:  Optional[float] = None

    candles_analyzed: int = 0
