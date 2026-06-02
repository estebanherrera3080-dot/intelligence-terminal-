"""
MacroTrend Engine — output schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MacroSnapshot(BaseModel):
    """Raw macro data point collected from providers."""
    timestamp: datetime

    xauusd:  float = Field(..., description="Gold spot price (USD)")
    dxy:     float = Field(..., description="US Dollar Index")
    us10y:   float = Field(..., description="10-Year Treasury Yield (%)")
    us02y:   float = Field(..., description="2-Year Treasury Yield (%)")
    spx:     float = Field(..., description="S&P 500 level")
    ndx:     float = Field(..., description="Nasdaq 100 level")
    vix:     float = Field(..., description="VIX Volatility Index")

    # Derived at snapshot time
    yield_curve:   float = Field(..., description="10Y - 2Y spread (%)")
    gold_dxy_ratio: float = Field(..., description="XAUUSD / DXY")


class ComponentScores(BaseModel):
    """Individual driver scores (0-100). Higher = more bullish for gold."""
    dxy:          int = Field(..., ge=0, le=100, description="Dollar weakness score")
    yield_curve:  int = Field(..., ge=0, le=100, description="Yield curve inversion signal")
    real_rates:   int = Field(..., ge=0, le=100, description="Real rates environment")
    vix_fear:     int = Field(..., ge=0, le=100, description="Fear/safe-haven demand")
    spx_momentum: int = Field(..., ge=0, le=100, description="Equity stress signal")
    gold_momentum: int = Field(..., ge=0, le=100, description="Gold own trend confirmation")


class MacroAnalysis(BaseModel):
    """
    Full MacroTrend Engine output — one analysis result.

    Scores:
        macro_score  0-100  Higher = macro environment more supportive for gold
        risk_score   0-100  Higher = more systemic risk / fear in markets

    Bias:
        Bullish  macro_score ≥ 65
        Neutral  35 < macro_score < 65
        Bearish  macro_score ≤ 35
    """

    timestamp: datetime

    # ── Primary outputs ────────────────────────────────────────────
    macro_score:  int   = Field(..., ge=0, le=100)
    risk_score:   int   = Field(..., ge=0, le=100)
    gold_bias:    str   = Field(..., description="bullish | neutral | bearish")
    confidence:   float = Field(..., ge=0, le=100, description="%")

    # ── Regime classifications ─────────────────────────────────────
    market_regime:       str = Field(..., description="risk_on | risk_off | transitional")
    macro_regime:        str = Field(
        ...,
        description=(
            "hawkish_fed | dovish_fed | inflationary | deflationary | "
            "recession_risk | growth_expansion | neutral"
        ),
    )
    liquidity_conditions: str = Field(..., description="abundant | normal | tight")

    # ── Component breakdown ────────────────────────────────────────
    components: ComponentScores
    snapshot:   MacroSnapshot

    # ── Human-readable signals ─────────────────────────────────────
    key_signals:  List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)

    # ── Scenario labels ────────────────────────────────────────────
    primary_scenario:  str = ""
    alternate_scenario: str = ""
