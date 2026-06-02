"""
Smart Money Engine — orchestrates all SMC detectors over live OHLCV data.
"""

from datetime import UTC, datetime
from typing import List, Optional

from app.core.logger import get_logger
from app.services.smc import detector as det
from app.services.smc.schemas import SMCAnalysis, SMCEvent
from app.services.market_data.providers.base import BaseMarketDataProvider

logger = get_logger(__name__)

_DEFAULT_TIMEFRAMES = ["1h", "4h"]
_LOOKBACK = 100   # candles per analysis run


class SmartMoneyEngine:
    """
    Runs all SMC detectors (BOS, CHoCH, FVG, OB, EQL/EQH, Sweeps)
    against recent OHLCV candles and aggregates a structural bias.
    """

    def __init__(self, provider: BaseMarketDataProvider) -> None:
        self.provider = provider

    async def analyze(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "1h",
        limit: int = _LOOKBACK,
    ) -> SMCAnalysis:
        candles = await self.provider.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)

        if not candles:
            return SMCAnalysis(symbol=symbol, timeframe=timeframe, timestamp=datetime.now(UTC))

        events:  List[SMCEvent] = []

        # ── BOS / CHoCH ────────────────────────────────────────────
        events += det.detect_bos_choch(candles, symbol, timeframe)

        # ── FVG ───────────────────────────────────────────────────
        fvg_zones = det.detect_fvg(candles, symbol, timeframe)

        # ── Order Blocks ──────────────────────────────────────────
        order_blocks = det.detect_order_blocks(candles, symbol, timeframe)

        # ── Liquidity ─────────────────────────────────────────────
        liq_levels, liq_events = det.detect_liquidity(candles, symbol, timeframe)
        events += liq_events

        # ── Structural Bias ───────────────────────────────────────
        structure_bias, bias_strength = self._compute_bias(events, fvg_zones, order_blocks)

        last_bos   = self._last_event_type(events, ("BOS_BULLISH", "BOS_BEARISH"))
        last_choch = self._last_event_type(events, ("CHOCH_BULLISH", "CHOCH_BEARISH"))

        current_price = candles[-1].close

        # Nearest zones relative to current price
        fvg_above = min(
            (z.bottom for z in fvg_zones if z.direction == "bearish" and z.bottom > current_price),
            default=None,
        )
        fvg_below = max(
            (z.top for z in fvg_zones if z.direction == "bullish" and z.top < current_price),
            default=None,
        )
        ob_above = min(
            (b.bottom for b in order_blocks if b.direction == "bearish" and b.bottom > current_price),
            default=None,
        )
        ob_below = max(
            (b.top for b in order_blocks if b.direction == "bullish" and b.top < current_price),
            default=None,
        )

        return SMCAnalysis(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(UTC),
            events=sorted(events, key=lambda e: e.timestamp),
            fvg_zones=fvg_zones,
            order_blocks=order_blocks,
            liquidity_levels=liq_levels,
            structure_bias=structure_bias,
            bias_strength=bias_strength,
            last_bos=last_bos,
            last_choch=last_choch,
            nearest_fvg_above=fvg_above,
            nearest_fvg_below=fvg_below,
            nearest_ob_above=ob_above,
            nearest_ob_below=ob_below,
            candles_analyzed=len(candles),
        )

    # ──────────────────────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────────────────────

    def _compute_bias(self, events, fvg_zones, order_blocks) -> tuple[str, float]:
        score = 50.0   # start neutral

        for e in events:
            if "BULLISH" in e.event_type:
                weight = 15 if "CHOCH" in e.event_type else 8
                score += weight * (e.intensity / 100)
            elif "BEARISH" in e.event_type:
                weight = 15 if "CHOCH" in e.event_type else 8
                score -= weight * (e.intensity / 100)
            elif e.event_type == "LIQUIDITY_SWEEP_LOW":
                score += 10 * (e.intensity / 100)
            elif e.event_type == "LIQUIDITY_SWEEP_HIGH":
                score -= 10 * (e.intensity / 100)

        # FVG imbalance tilt
        bull_fvg = sum(z.intensity for z in fvg_zones if z.direction == "bullish")
        bear_fvg = sum(z.intensity for z in fvg_zones if z.direction == "bearish")
        score += (bull_fvg - bear_fvg) * 0.05

        score = max(0.0, min(100.0, score))

        if score >= 62:
            return "bullish", score
        if score <= 38:
            return "bearish", 100 - score
        return "neutral", abs(score - 50) * 2

    def _last_event_type(self, events: List[SMCEvent], types: tuple) -> Optional[str]:
        for e in reversed(events):
            if e.event_type in types:
                return "bullish" if "BULLISH" in e.event_type else "bearish"
        return None
