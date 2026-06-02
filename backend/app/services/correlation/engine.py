"""
Correlation Engine — orchestrates data collection and analysis.
"""

from datetime import UTC, datetime
from typing import Dict, List

from app.core.logger import get_logger
from app.services.correlation import calculator as calc
from app.services.correlation.schemas import CorrelationAnalysis
from app.services.market_data.providers.base import BaseMarketDataProvider

logger = get_logger(__name__)

_LOOKBACK  = 80
_TIMEFRAME = "1h"

# All pairs to analyze (always include gold on one side)
_PAIRS = [
    ("XAUUSD", "DXY"),
    ("XAUUSD", "US10Y"),
    ("XAUUSD", "US02Y"),
    ("XAUUSD", "SPX"),
    ("XAUUSD", "VIX"),
    ("XAUUSD", "NDX"),
    ("DXY",    "US10Y"),
    ("SPX",    "VIX"),
]

_ALL_SYMBOLS = list({s for pair in _PAIRS for s in pair})


class CorrelationEngine:
    def __init__(self, provider: BaseMarketDataProvider) -> None:
        self.provider = provider

    async def analyze(self, limit: int = _LOOKBACK) -> CorrelationAnalysis:
        now = datetime.now(UTC)

        # ── Fetch all price series ─────────────────────────────────
        prices: Dict[str, List[float]] = {}
        for sym in _ALL_SYMBOLS:
            try:
                candles = await self.provider.fetch_ohlcv(
                    symbol=sym, timeframe=_TIMEFRAME, limit=limit
                )
                prices[sym] = [c.close for c in candles]
            except Exception as e:
                logger.warning(f"Correlation: failed to fetch {sym}: {e}")
                prices[sym] = []

        # ── Pair correlations ──────────────────────────────────────
        pairs = []
        for sym_a, sym_b in _PAIRS:
            pair = calc.analyze_pair(sym_a, sym_b, prices.get(sym_a, []), prices.get(sym_b, []))
            if pair:
                pairs.append(pair)

        # ── Breakdown detection ────────────────────────────────────
        breakdowns = calc.detect_breakdowns(pairs, now)

        # ── Gold profile ───────────────────────────────────────────
        other = {s: prices[s] for s in _ALL_SYMBOLS if s != "XAUUSD" and prices.get(s)}
        gold_profile = calc.build_gold_profile(prices.get("XAUUSD", []), other, now)

        # ── Regime ────────────────────────────────────────────────
        regime, score = calc.classify_correlation_regime(pairs, breakdowns)
        signal = calc.dominant_signal(pairs, gold_profile)

        return CorrelationAnalysis(
            timestamp=now,
            pairs=pairs,
            breakdown_events=breakdowns,
            gold_profile=gold_profile,
            regime=regime,
            regime_score=score,
            dominant_signal=signal,
            candles_used=limit,
        )
