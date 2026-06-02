"""
Volatility Engine — output schemas.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class VolatilityReading(BaseModel):
    """Volatility metrics for a single symbol/timeframe."""

    symbol:    str
    timeframe: str
    timestamp: datetime

    # ── ATR ────────────────────────────────────────────────────────
    atr:        float = Field(..., description="Average True Range (absolute)")
    atr_pct:    float = Field(..., description="ATR as % of current price")
    atr_14:     float = Field(..., description="14-period ATR")
    atr_zscore: float = Field(..., description="ATR z-score vs 50-period history")

    # ── Realized Volatility ────────────────────────────────────────
    realized_vol_10:  float = Field(..., description="10-period annualized realized vol %")
    realized_vol_20:  float = Field(..., description="20-period annualized realized vol %")
    realized_vol_50:  float = Field(..., description="50-period annualized realized vol %")

    # ── Range Analysis ─────────────────────────────────────────────
    candle_range_pct:    float = Field(..., description="Current candle H-L as % of price")
    avg_range_20:        float = Field(..., description="20-period avg candle range %")
    range_compression:   float = Field(..., description="Current range / avg range (< 1 = compressed)")
    body_to_range_ratio: float = Field(..., description="Candle body / total range (0-1)")

    # ── Regime ─────────────────────────────────────────────────────
    regime:           str   = Field(..., description="low | medium | high | expansion | compression")
    regime_score:     float = Field(..., description="0-100, higher = more volatile")
    compression_score: float = Field(..., description="0-100, higher = more compressed")
    expansion_score:  float = Field(..., description="0-100, higher = expanding")

    # ── Signals ────────────────────────────────────────────────────
    signals: List[str] = Field(default_factory=list)
    candles_analyzed: int = 0


class VolatilitySummary(BaseModel):
    """Multi-symbol volatility summary for the dashboard."""
    timestamp: datetime
    readings: dict   # symbol → VolatilityReading
    gold_regime:     str
    gold_vol_score:  float
    market_vol_regime: str   # calm | normal | elevated | extreme
    vix_level:       float
    vix_regime:      str     # low | normal | elevated | spike
