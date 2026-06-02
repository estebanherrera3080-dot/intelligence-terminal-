"""
Smart Money Concepts detector — pure functions over OHLCV candle lists.

Each detector receives a list of OHLCVData (chronological order, oldest first)
and returns detected structures. No external dependencies beyond stdlib.

Implemented:
  - Break of Structure (BOS)     — continuation signal
  - Change of Character (CHoCH)  — reversal signal
  - Fair Value Gap (FVG)         — imbalance / liquidity magnet
  - Order Blocks (OB)            — institutional supply/demand zones
  - Equal Highs / Equal Lows     — liquidity pools
  - Liquidity Sweeps             — stop-hunt detection
"""

from datetime import datetime
from typing import List, Optional, Tuple

from app.schemas.market import OHLCVData
from app.services.smc.schemas import (
    FVGZone, LiquidityLevel, OrderBlock, SMCEvent,
)


# ── Tolerance for "equal" highs/lows (0.05% of price) ──────────────
_EQ_TOLERANCE = 0.0005


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


# ──────────────────────────────────────────────────────────────────
#  Swing High / Low detection
# ──────────────────────────────────────────────────────────────────

def find_swing_highs(candles: List[OHLCVData], left: int = 2, right: int = 2) -> List[int]:
    """Return indices of swing highs (local maxima over left+right window)."""
    result = []
    for i in range(left, len(candles) - right):
        h = candles[i].high
        if all(h > candles[i - j].high for j in range(1, left + 1)) and \
           all(h > candles[i + j].high for j in range(1, right + 1)):
            result.append(i)
    return result


def find_swing_lows(candles: List[OHLCVData], left: int = 2, right: int = 2) -> List[int]:
    """Return indices of swing lows (local minima)."""
    result = []
    for i in range(left, len(candles) - right):
        lo = candles[i].low
        if all(lo < candles[i - j].low for j in range(1, left + 1)) and \
           all(lo < candles[i + j].low for j in range(1, right + 1)):
            result.append(i)
    return result


# ──────────────────────────────────────────────────────────────────
#  Break of Structure (BOS) & Change of Character (CHoCH)
# ──────────────────────────────────────────────────────────────────

def detect_bos_choch(
    candles: List[OHLCVData], symbol: str, timeframe: str
) -> List[SMCEvent]:
    """
    BOS  — price breaks a swing high/low in the direction of the current trend.
           Confirms trend continuation.
    CHoCH — price breaks a swing high/low AGAINST the current trend.
            Signals potential trend reversal.

    Algorithm:
      1. Find swing highs and lows.
      2. Track trend: series of HH+HL = uptrend, LH+LL = downtrend.
      3. When current candle close breaks a previous swing:
         - Same direction as trend → BOS
         - Opposite direction → CHoCH
    """
    events: List[SMCEvent] = []
    if len(candles) < 10:
        return events

    swing_highs = find_swing_highs(candles, left=3, right=2)
    swing_lows  = find_swing_lows(candles,  left=3, right=2)

    # Determine trend from last two swing highs and lows
    trend = "neutral"
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        hh = candles[swing_highs[-1]].high > candles[swing_highs[-2]].high
        hl = candles[swing_lows[-1]].low  > candles[swing_lows[-2]].low
        lh = candles[swing_highs[-1]].high < candles[swing_highs[-2]].high
        ll = candles[swing_lows[-1]].low  < candles[swing_lows[-2]].low
        if hh and hl:
            trend = "bullish"
        elif lh and ll:
            trend = "bearish"

    # Check most recent candle against last confirmed swing levels
    last = candles[-1]

    if swing_highs:
        last_sh_price = candles[swing_highs[-1]].high
        last_sh_ts    = candles[swing_highs[-1]].timestamp
        if last.close > last_sh_price:
            move_size = (last.close - last_sh_price) / last_sh_price * 100
            intensity = _clamp(move_size * 20)
            etype = "BOS_BULLISH" if trend == "bullish" else "CHOCH_BULLISH"
            events.append(SMCEvent(
                event_type=etype,
                timestamp=last.timestamp,
                price=last_sh_price,
                high=last.high,
                low=last.low,
                intensity=intensity,
                probability=_clamp(65 + intensity * 0.3),
                timeframe=timeframe,
                symbol=symbol,
                description=f"Close {last.close:.2f} broke swing high {last_sh_price:.2f} — {etype}",
            ))

    if swing_lows:
        last_sl_price = candles[swing_lows[-1]].low
        if last.close < last_sl_price:
            move_size = (last_sl_price - last.close) / last_sl_price * 100
            intensity = _clamp(move_size * 20)
            etype = "BOS_BEARISH" if trend == "bearish" else "CHOCH_BEARISH"
            events.append(SMCEvent(
                event_type=etype,
                timestamp=last.timestamp,
                price=last_sl_price,
                high=last.high,
                low=last.low,
                intensity=intensity,
                probability=_clamp(65 + intensity * 0.3),
                timeframe=timeframe,
                symbol=symbol,
                description=f"Close {last.close:.2f} broke swing low {last_sl_price:.2f} — {etype}",
            ))

    return events


# ──────────────────────────────────────────────────────────────────
#  Fair Value Gap (FVG)
# ──────────────────────────────────────────────────────────────────

def detect_fvg(
    candles: List[OHLCVData], symbol: str, timeframe: str,
    min_gap_pct: float = 0.05,
) -> List[FVGZone]:
    """
    Bullish FVG: candle[i+2].low > candle[i].high  → gap between them.
    Bearish FVG: candle[i+2].high < candle[i].low  → gap between them.
    min_gap_pct: minimum gap as % of price to filter noise.
    """
    zones: List[FVGZone] = []
    for i in range(len(candles) - 2):
        c0, c1, c2 = candles[i], candles[i + 1], candles[i + 2]

        # Bullish FVG
        if c2.low > c0.high:
            gap = c2.low - c0.high
            gap_pct = gap / c0.high * 100
            if gap_pct >= min_gap_pct:
                midpoint = (c0.high + c2.low) / 2
                intensity = _clamp(gap_pct * 10)
                zones.append(FVGZone(
                    direction="bullish",
                    top=c2.low, bottom=c0.high, midpoint=midpoint,
                    gap_size=gap, gap_pct=round(gap_pct, 4),
                    timestamp=c1.timestamp,
                    intensity=intensity,
                ))

        # Bearish FVG
        elif c2.high < c0.low:
            gap = c0.low - c2.high
            gap_pct = gap / c0.low * 100
            if gap_pct >= min_gap_pct:
                midpoint = (c0.low + c2.high) / 2
                intensity = _clamp(gap_pct * 10)
                zones.append(FVGZone(
                    direction="bearish",
                    top=c0.low, bottom=c2.high, midpoint=midpoint,
                    gap_size=gap, gap_pct=round(gap_pct, 4),
                    timestamp=c1.timestamp,
                    intensity=intensity,
                ))

    return zones[-10:]   # keep last 10 most recent


# ──────────────────────────────────────────────────────────────────
#  Order Blocks (OB)
# ──────────────────────────────────────────────────────────────────

def detect_order_blocks(
    candles: List[OHLCVData], symbol: str, timeframe: str,
    min_move_pct: float = 0.3,
) -> List[OrderBlock]:
    """
    Bullish OB: last bearish candle before a strong bullish impulse.
    Bearish OB: last bullish candle before a strong bearish impulse.
    The OB body becomes a supply/demand zone.
    min_move_pct: minimum impulse size to qualify a candle as OB origin.
    """
    blocks: List[OrderBlock] = []
    if len(candles) < 4:
        return blocks

    for i in range(1, len(candles) - 2):
        c      = candles[i]
        c_next = candles[i + 1]
        c_prev = candles[i - 1]

        # Measure impulse after the OB candle
        impulse = abs(c_next.close - c_next.open) / c_next.open * 100

        if impulse < min_move_pct:
            continue

        # Bullish OB: bearish candle (c) followed by strong bullish impulse
        if c.close < c.open and c_next.close > c_next.open:
            strength = _clamp(impulse * 10)
            blocks.append(OrderBlock(
                direction="bullish",
                top=c.open, bottom=c.close, midpoint=(c.open + c.close) / 2,
                timestamp=c.timestamp,
                strength=strength,
            ))

        # Bearish OB: bullish candle (c) followed by strong bearish impulse
        elif c.close > c.open and c_next.close < c_next.open:
            strength = _clamp(impulse * 10)
            blocks.append(OrderBlock(
                direction="bearish",
                top=c.close, bottom=c.open, midpoint=(c.open + c.close) / 2,
                timestamp=c.timestamp,
                strength=strength,
            ))

    return blocks[-6:]


# ──────────────────────────────────────────────────────────────────
#  Equal Highs / Equal Lows & Liquidity Sweeps
# ──────────────────────────────────────────────────────────────────

def detect_liquidity(
    candles: List[OHLCVData], symbol: str, timeframe: str,
) -> Tuple[List[LiquidityLevel], List[SMCEvent]]:
    """
    Equal Highs/Lows: two or more swing points within _EQ_TOLERANCE of each other.
    Liquidity Sweep: a wick that exceeds a previous swing high/low then closes back.
    """
    levels:  List[LiquidityLevel] = []
    events:  List[SMCEvent]       = []

    swing_highs = find_swing_highs(candles, left=3, right=2)
    swing_lows  = find_swing_lows(candles,  left=3, right=2)

    # Equal Highs
    sh_prices = [(i, candles[i].high) for i in swing_highs]
    for j in range(len(sh_prices)):
        idx, p = sh_prices[j]
        touches = sum(1 for _, q in sh_prices if abs(q - p) / p <= _EQ_TOLERANCE)
        if touches >= 2:
            levels.append(LiquidityLevel(
                level_type="equal_highs",
                price=p, touches=touches,
                timestamp=candles[idx].timestamp,
                intensity=_clamp(touches * 25),
            ))
            break  # one cluster per scan

    # Equal Lows
    sl_prices = [(i, candles[i].low) for i in swing_lows]
    for j in range(len(sl_prices)):
        idx, p = sl_prices[j]
        touches = sum(1 for _, q in sl_prices if abs(q - p) / p <= _EQ_TOLERANCE)
        if touches >= 2:
            levels.append(LiquidityLevel(
                level_type="equal_lows",
                price=p, touches=touches,
                timestamp=candles[idx].timestamp,
                intensity=_clamp(touches * 25),
            ))
            break

    # Liquidity Sweeps — wick exceeds swing then close reverses
    last = candles[-1]
    if swing_highs:
        sh_price = candles[swing_highs[-1]].high
        if last.high > sh_price and last.close < sh_price:
            sweep_size = (last.high - sh_price) / sh_price * 100
            events.append(SMCEvent(
                event_type="LIQUIDITY_SWEEP_HIGH",
                timestamp=last.timestamp,
                price=sh_price,
                high=last.high,
                low=last.low,
                intensity=_clamp(sweep_size * 30),
                probability=72.0,
                timeframe=timeframe, symbol=symbol,
                description=f"Wick swept highs at {sh_price:.2f}, closed below → bearish reversal signal",
            ))
    if swing_lows:
        sl_price = candles[swing_lows[-1]].low
        if last.low < sl_price and last.close > sl_price:
            sweep_size = (sl_price - last.low) / sl_price * 100
            events.append(SMCEvent(
                event_type="LIQUIDITY_SWEEP_LOW",
                timestamp=last.timestamp,
                price=sl_price,
                high=last.high,
                low=last.low,
                intensity=_clamp(sweep_size * 30),
                probability=72.0,
                timeframe=timeframe, symbol=symbol,
                description=f"Wick swept lows at {sl_price:.2f}, closed above → bullish reversal signal",
            ))

    return levels, events
