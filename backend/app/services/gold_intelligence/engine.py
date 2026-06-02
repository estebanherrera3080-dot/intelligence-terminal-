"""
Gold Intelligence Engine — orchestrates all modules into a unified
multi-timeframe conviction score for XAUUSD.

Data flow:
  1. Fetch candles for 5m, 15m, 1h
  2. Run MacroTrend Engine → macro context
  3. Per-timeframe: Momentum + SMC + Volatility + Macro Alignment
  4. Consensus: weighted score + alignment label
  5. Key insight narrative

Timeframe weights (institutional):
  5m    10%  — entry timing only
  15m   20%  — microstructure
  1h    35%  — primary trading TF for gold
  macro 35%  — dominant driver (gold is a macro asset)
"""

from datetime import UTC, datetime
from typing import List

from app.core.logger import get_logger
from app.services.gold_intelligence.analyzer import analyze_timeframe
from app.services.gold_intelligence.schemas import ConsensusResult, HorizonBias
from app.services.macro.engine import MacroTrendEngine
from app.services.market_data.providers.base import BaseMarketDataProvider

logger = get_logger(__name__)

_WEIGHTS = {"5m": 0.10, "15m": 0.20, "1h": 0.35, "macro": 0.35}
_LABELS  = {"5m": "5 Min", "15m": "15 Min", "1h": "1 Hour", "macro": "Macro"}
_CANDLES = {"5m": 60, "15m": 60, "1h": 80}

SYMBOL = "XAUUSD"


class GoldIntelligenceEngine:
    def __init__(self, provider: BaseMarketDataProvider) -> None:
        self.provider     = provider
        self.macro_engine = MacroTrendEngine(provider)

    async def analyze(self) -> ConsensusResult:
        now = datetime.now(UTC)

        # ── 1. Macro context ──────────────────────────────────────
        macro_analysis = await self.macro_engine.analyze()
        macro_score    = macro_analysis.macro_score
        macro_bias     = macro_analysis.gold_bias

        # ── 2. Macro horizon bias (from MacroTrend output) ────────
        macro_horizon = HorizonBias(
            horizon="macro", timeframe_label=_LABELS["macro"],
            conviction_score=macro_score,
            bias=macro_bias,
            confidence=macro_analysis.confidence,
            regime=macro_analysis.macro_regime,
            drivers=[
                f"Market: {macro_analysis.market_regime}",
                f"Macro: {macro_analysis.macro_regime}",
                f"Liquidity: {macro_analysis.liquidity_conditions}",
            ],
            momentum_score=macro_analysis.components.spx_momentum,
            structure_score=macro_analysis.components.yield_curve,
            volatility_score=macro_analysis.components.vix_fear,
            macro_alignment=100,  # macro is the reference, always self-aligned
        )

        # ── 3. Intraday timeframes ────────────────────────────────
        horizons: dict[str, HorizonBias] = {}
        for tf, limit in _CANDLES.items():
            try:
                candles = await self.provider.fetch_ohlcv(
                    symbol=SYMBOL, timeframe=tf, limit=limit
                )
                horizons[tf] = analyze_timeframe(
                    candles=candles,
                    symbol=SYMBOL,
                    timeframe=tf,
                    label=_LABELS[tf],
                    macro_score=macro_score,
                    macro_bias=macro_bias,
                )
            except Exception as e:
                logger.warning(f"GoldIntelligence: failed to analyze {tf}: {e}")
                horizons[tf] = _neutral_horizon(tf, _LABELS[tf])

        # ── 4. Consensus ──────────────────────────────────────────
        all_horizons = {**horizons, "macro": macro_horizon}
        consensus_score = _weighted_score(all_horizons)
        consensus_bias  = _majority_bias(all_horizons)
        alignment       = _alignment_label(all_horizons)
        confidence      = _consensus_confidence(all_horizons, alignment)
        dominant        = max(all_horizons, key=lambda k: abs(all_horizons[k].conviction_score - 50))
        insight         = _key_insight(horizons, macro_horizon, consensus_bias, alignment)

        return ConsensusResult(
            timestamp=now,
            m5=horizons["5m"], m15=horizons["15m"], h1=horizons["1h"],
            macro=macro_horizon,
            consensus_score=consensus_score,
            consensus_bias=consensus_bias,
            alignment=alignment,
            confidence=confidence,
            dominant_timeframe=_LABELS[dominant],
            key_insight=insight,
        )


# ── Consensus helpers ─────────────────────────────────────────────

def _weighted_score(horizons: dict) -> int:
    total = sum(
        horizons[tf].conviction_score * w
        for tf, w in _WEIGHTS.items()
        if tf in horizons
    )
    return int(max(0, min(100, total)))


def _majority_bias(horizons: dict) -> str:
    votes = [h.bias for h in horizons.values()]
    bullish = votes.count("bullish")
    bearish = votes.count("bearish")
    neutral = votes.count("neutral")

    # Absolute majority (≥3 of 4)
    if bullish >= 3:
        return "bullish"
    if bearish >= 3:
        return "bearish"
    if neutral >= 3:
        return "neutral"

    # Relative majority — must beat BOTH other camps
    if bullish > bearish and bullish > neutral:
        return "bullish"
    if bearish > bullish and bearish > neutral:
        return "bearish"

    return "neutral"


def _alignment_label(horizons: dict) -> str:
    biases = {h.bias for h in horizons.values()}
    if len(biases) == 1:
        return "aligned"
    votes = [h.bias for h in horizons.values()]
    dominant_count = max(votes.count(b) for b in biases)
    if dominant_count >= 3:
        return "mixed"
    return "conflicted"


def _consensus_confidence(horizons: dict, alignment: str) -> float:
    base = sum(h.confidence for h in horizons.values()) / len(horizons)
    penalty = {"aligned": 0, "mixed": -10, "conflicted": -22}[alignment]
    return round(max(20.0, base + penalty), 1)


def _key_insight(
    intraday: dict, macro: HorizonBias,
    consensus_bias: str, alignment: str,
) -> str:
    m5_bias  = intraday.get("5m", macro).bias
    m15_bias = intraday.get("15m", macro).bias
    h1_bias  = intraday.get("1h", macro).bias
    mac_bias = macro.bias

    if alignment == "aligned":
        return (
            f"All timeframes {consensus_bias} - institutional alignment "
            f"from macro through 5m. Highest conviction setup."
        )
    if mac_bias != consensus_bias and alignment == "mixed":
        return (
            f"Macro is {mac_bias} while intraday shows {consensus_bias} pressure. "
            "Counter-trend intraday move - trade with caution, macro wins medium-term."
        )
    if m5_bias == m15_bias and m5_bias != h1_bias:
        return (
            f"5m/15m aligned {m5_bias} against {h1_bias} 1h trend. "
            "Possible pullback/retest before macro direction resumes."
        )
    if h1_bias == mac_bias and h1_bias != m5_bias:
        return (
            f"1h and macro both {h1_bias}. 5m noise going {m5_bias}. "
            "Wait for 5m to align with higher timeframe before entry."
        )
    return (
        f"Conflicted signals across timeframes. "
        f"Macro {mac_bias}, 1h {h1_bias}, 15m {m15_bias}, 5m {m5_bias}. "
        "Await resolution before positioning."
    )


def _neutral_horizon(tf: str, label: str) -> HorizonBias:
    return HorizonBias(
        horizon=tf, timeframe_label=label,
        conviction_score=50, bias="neutral", confidence=50.0,
        regime="unknown", drivers=["Insufficient data"],
    )
