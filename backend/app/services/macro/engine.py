"""
MacroTrend Engine — orchestrates data collection and analysis.

Usage:
    engine = MacroTrendEngine(provider)
    result = await engine.analyze()
"""

from datetime import UTC, datetime
from typing import Dict, List

from app.core.logger import get_logger
from app.services.macro import indicators as ind
from app.services.macro.schemas import (
    ComponentScores, MacroAnalysis, MacroSnapshot,
)
from app.services.market_data.providers.base import BaseMarketDataProvider

logger = get_logger(__name__)

# Candle history needed for momentum calculations
_LOOKBACK = 30
_TIMEFRAME = "1h"

# Ordered list of symbols required by this engine
_REQUIRED_SYMBOLS = ["XAUUSD", "DXY", "US10Y", "US02Y", "SPX", "NDX", "VIX"]


class MacroTrendEngine:
    """
    Institutional macro analysis engine.

    Workflow:
      1. Fetch recent OHLCV for all 7 instruments
      2. Compute per-indicator scores
      3. Aggregate → macro_score, risk_score
      4. Classify regimes
      5. Determine gold bias + confidence
      6. Generate narrative signals and scenarios
    """

    def __init__(self, provider: BaseMarketDataProvider) -> None:
        self.provider = provider

    # ──────────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────────

    async def analyze(self) -> MacroAnalysis:
        """Run a full macro analysis cycle and return a MacroAnalysis result."""
        data = await self._fetch_all()
        return self._compute(data)

    # ──────────────────────────────────────────────────────────────
    #  Data collection
    # ──────────────────────────────────────────────────────────────

    async def _fetch_all(self) -> Dict[str, List[float]]:
        """
        Fetch close-price series for each symbol.
        Errors per-symbol are caught; missing data is replaced with an empty list
        so the indicator layer can degrade gracefully.
        """
        series: Dict[str, List[float]] = {}
        for sym in _REQUIRED_SYMBOLS:
            try:
                candles = await self.provider.fetch_ohlcv(
                    symbol=sym, timeframe=_TIMEFRAME, limit=_LOOKBACK
                )
                series[sym] = [c.close for c in candles] if candles else []
            except Exception as e:
                logger.warning(f"MacroEngine: failed to fetch {sym}: {e}")
                series[sym] = []
        return series

    # ──────────────────────────────────────────────────────────────
    #  Computation
    # ──────────────────────────────────────────────────────────────

    def _latest(self, series: List[float], fallback: float = 0.0) -> float:
        return series[-1] if series else fallback

    def _compute(self, data: Dict[str, List[float]]) -> MacroAnalysis:
        now = datetime.now(UTC)

        # ── Current values ─────────────────────────────────────────
        xauusd = self._latest(data["XAUUSD"], 2050.0)
        dxy    = self._latest(data["DXY"],    104.5)
        us10y  = self._latest(data["US10Y"],   4.35)
        us02y  = self._latest(data["US02Y"],   4.85)
        spx    = self._latest(data["SPX"],    5250.0)
        ndx    = self._latest(data["NDX"],   18400.0)
        vix    = self._latest(data["VIX"],     15.5)

        yield_spread = round(us10y - us02y, 4)
        gold_dxy_ratio = round(xauusd / dxy, 4) if dxy else 0.0

        # Momentum values needed for regime classification
        spx_mom  = ind._momentum(data["SPX"],   window=min(20, max(0, len(data["SPX"])  - 1)))
        dxy_mom  = ind._momentum(data["DXY"],   window=min(20, max(0, len(data["DXY"])  - 1)))
        us10y_mom = ind._momentum(data["US10Y"], window=min(20, max(0, len(data["US10Y"]) - 1)))

        # ── Component scores ───────────────────────────────────────
        c_dxy   = ind.score_dxy(dxy,   data["DXY"])
        c_yc    = ind.score_yield_curve(us10y, us02y)
        c_rr    = ind.score_real_rates(us10y, data["US10Y"])
        c_vix   = ind.score_vix(vix)
        c_spx   = ind.score_spx_momentum(data["SPX"])
        c_gold  = ind.score_gold_momentum(data["XAUUSD"])

        components_dict = {
            "dxy":          c_dxy,
            "yield_curve":  c_yc,
            "real_rates":   c_rr,
            "vix_fear":     c_vix,
            "spx_momentum": c_spx,
            "gold_momentum": c_gold,
        }

        # ── Aggregate scores ───────────────────────────────────────
        macro_score = ind.compute_macro_score(components_dict)
        risk_score  = ind.compute_risk_score(vix, yield_spread, spx_mom)

        # ── Regime classification ──────────────────────────────────
        market_regime = ind.classify_market_regime(vix, spx_mom, dxy_mom)
        macro_regime  = ind.classify_macro_regime(
            us10y, us02y, us10y_mom, dxy_mom, vix, spx_mom
        )
        liquidity     = ind.classify_liquidity(us10y, vix, dxy)
        gold_bias     = ind.classify_gold_bias(macro_score, risk_score)
        confidence    = ind.compute_confidence(components_dict, macro_score)

        # ── Narrative ─────────────────────────────────────────────
        signals, risks = ind.generate_signals(
            c_dxy, c_yc, c_rr, c_vix, c_spx,
            yield_spread, vix, us10y, dxy, spx_mom,
        )
        primary_scenario, alternate_scenario = ind.generate_scenarios(
            gold_bias, macro_regime, market_regime
        )

        return MacroAnalysis(
            timestamp=now,
            macro_score=macro_score,
            risk_score=risk_score,
            gold_bias=gold_bias,
            confidence=confidence,
            market_regime=market_regime,
            macro_regime=macro_regime,
            liquidity_conditions=liquidity,
            components=ComponentScores(
                dxy=c_dxy,
                yield_curve=c_yc,
                real_rates=c_rr,
                vix_fear=c_vix,
                spx_momentum=c_spx,
                gold_momentum=c_gold,
            ),
            snapshot=MacroSnapshot(
                timestamp=now,
                xauusd=xauusd, dxy=dxy,
                us10y=us10y,   us02y=us02y,
                spx=spx,       ndx=ndx, vix=vix,
                yield_curve=yield_spread,
                gold_dxy_ratio=gold_dxy_ratio,
            ),
            key_signals=signals,
            risk_factors=risks,
            primary_scenario=primary_scenario,
            alternate_scenario=alternate_scenario,
        )
