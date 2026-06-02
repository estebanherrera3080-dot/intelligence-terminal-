"""
Per-timeframe bias analyzer — pure functions over OHLCV candles.

Each analyzer produces a conviction_score (0-100) and bias string.
Higher score = more bullish. 50 = neutral.
"""

import math
from typing import List, Tuple

from app.schemas.market import OHLCVData
from app.services.smc import detector as smc_det
from app.services.volatility import calculator as vol_calc


# ── Primitives ────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> int:
    return int(max(lo, min(hi, v)))


def _bias_from_score(score: int) -> str:
    if score >= 60:
        return "bullish"
    if score <= 40:
        return "bearish"
    return "neutral"


def _momentum_score(candles: List[OHLCVData], fast: int = 5, slow: int = 20) -> int:
    """
    Momentum conviction 0-100 (50 = neutral).
    Uses fast/slow price momentum + close vs midpoint of range.
    """
    if len(candles) < slow + 1:
        return 50

    prices = [c.close for c in candles]

    # Fast momentum: last `fast` candles
    fast_mom = (prices[-1] - prices[-fast - 1]) / prices[-fast - 1] * 100
    # Slow momentum: last `slow` candles
    slow_mom = (prices[-1] - prices[-slow - 1]) / prices[-slow - 1] * 100

    # Close position within recent range (0=bottom, 1=top)
    recent = candles[-slow:]
    hi  = max(c.high  for c in recent)
    lo  = min(c.low   for c in recent)
    pos = (prices[-1] - lo) / (hi - lo) if hi > lo else 0.5

    # Combine: momentum direction + range position
    mom_score = 50 + fast_mom * 8 + slow_mom * 3
    pos_score = pos * 100   # 0-100

    combined = 0.55 * mom_score + 0.45 * pos_score
    return _clamp(combined)


def _structure_score(candles: List[OHLCVData], symbol: str, timeframe: str) -> Tuple[int, str]:
    """
    SMC structure conviction 0-100.
    Uses BOS/CHoCH direction, FVG imbalance, swing position.
    Returns (score, regime_label).
    """
    if len(candles) < 15:
        return 50, "insufficient_data"

    score = 50.0
    regime = "neutral"

    # BOS / CHoCH
    events = smc_det.detect_bos_choch(candles, symbol, timeframe)
    for e in events[-3:]:  # last 3 events weighted most
        weight = e.intensity / 100 * 15
        if "BULLISH" in e.event_type:
            score += weight * (1.5 if "CHOCH" in e.event_type else 1.0)
            regime = "bullish_structure"
        else:
            score -= weight * (1.5 if "CHOCH" in e.event_type else 1.0)
            regime = "bearish_structure"

    # FVG imbalance — price below bullish FVG = bullish magnet
    fvg_zones = smc_det.detect_fvg(candles, symbol, timeframe)
    current   = candles[-1].close
    bull_fvgs = [z for z in fvg_zones if z.direction == "bullish" and z.top < current]
    bear_fvgs = [z for z in fvg_zones if z.direction == "bearish" and z.bottom > current]
    score += len(bull_fvgs) * 3   # bullish FVGs below = support
    score -= len(bear_fvgs) * 3   # bearish FVGs above = resistance

    # Liquidity sweeps signal reversal
    _, liq_events = smc_det.detect_liquidity(candles, symbol, timeframe)
    for e in liq_events:
        if e.event_type == "LIQUIDITY_SWEEP_LOW":
            score += e.intensity / 100 * 10    # swept lows = bullish
        elif e.event_type == "LIQUIDITY_SWEEP_HIGH":
            score -= e.intensity / 100 * 10   # swept highs = bearish

    # Swing position: price above/below most recent swing midpoint
    sh = smc_det.find_swing_highs(candles)
    sl = smc_det.find_swing_lows(candles)
    if sh and sl:
        last_sh = candles[sh[-1]].high
        last_sl = candles[sl[-1]].low
        midpoint = (last_sh + last_sl) / 2
        if current > midpoint:
            score += 5
        else:
            score -= 5

    return _clamp(score), regime


def _volatility_conviction(candles: List[OHLCVData]) -> Tuple[int, str]:
    """
    Volatility modifies conviction: expansion = high conviction, compression = low.
    Returns (modifier_score, regime_label).

    In expansion: conviction follows direction (score closer to extremes).
    In compression: conviction is pulled toward 50 (uncertainty).
    """
    if len(candles) < 20:
        return 50, "unknown"

    atr_series = vol_calc.compute_atr(candles, period=14)
    if not atr_series:
        return 50, "unknown"

    atr = atr_series[-1]
    price = candles[-1].close or 1.0
    atr_pct = atr / price * 100

    atr_hist = atr_series[-30:] if len(atr_series) >= 30 else atr_series
    atr_z = vol_calc._zscore(atr, atr_hist)

    # Range compression: recent range vs 20-period avg
    cr_pct = vol_calc.candle_range_pct(candles[-1])
    avg_r  = vol_calc.avg_range_pct(candles, 20)
    compression = cr_pct / avg_r if avg_r > 0 else 1.0

    regime_name, vol_score, comp_score, exp_score = vol_calc.classify_vol_regime(
        atr_pct, atr_z, 0, compression
    )

    # Conviction modifier: expansion → amplify signals, compression → dampen
    modifier = int(50 + (exp_score - comp_score) * 0.2)
    return _clamp(modifier), regime_name


def _macro_alignment_score(
    horizon_score: int,
    macro_score:   int,
    macro_bias:    str,
) -> int:
    """
    How well does this timeframe's direction align with macro context?
    Returns 0-100 (50 = neutral, >50 = macro confirms this TF).
    """
    # Same direction → high alignment
    tf_bias  = _bias_from_score(horizon_score)
    aligns   = tf_bias == macro_bias
    opposite = (
        (tf_bias == "bullish" and macro_bias == "bearish") or
        (tf_bias == "bearish" and macro_bias == "bullish")
    )

    if aligns:
        return _clamp(50 + abs(macro_score - 50) * 0.8)
    if opposite:
        return _clamp(50 - abs(macro_score - 50) * 0.8)
    return 50


def _confidence(mom: int, struct: int, vol_mod: int, alignment: int) -> float:
    """
    Confidence = agreement between components + macro alignment strength.
    """
    scores = [mom, struct, vol_mod, alignment]
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std = math.sqrt(variance)

    # Low dispersion = high agreement = high confidence
    agreement = max(0.0, 90.0 - std * 1.2)
    # Strength of conviction (distance from 50)
    extremity = abs(mean - 50) / 50 * 20

    return round(min(96.0, agreement + extremity), 1)


def _drivers(
    mom: int, struct: int, vol_mod: int, alignment: int,
    struct_regime: str, vol_regime: str,
) -> List[str]:
    parts = []
    if abs(mom - 50) > 15:
        parts.append(f"Momentum {'bullish' if mom > 50 else 'bearish'} ({mom})")
    if abs(struct - 50) > 10:
        parts.append(f"Structure: {struct_regime.replace('_', ' ')} ({struct})")
    if vol_regime in ("expansion", "compression"):
        parts.append(f"Volatility: {vol_regime}")
    if alignment > 65:
        parts.append("Macro confirms direction")
    elif alignment < 35:
        parts.append("Macro contradicts - reduced conviction")
    return parts[:3]


# ── Main entry point ──────────────────────────────────────────────

def analyze_timeframe(
    candles:     List[OHLCVData],
    symbol:      str,
    timeframe:   str,
    label:       str,
    macro_score: int,
    macro_bias:  str,
) -> "HorizonBias":
    """Compute full bias for one timeframe, incorporating macro context."""
    from app.services.gold_intelligence.schemas import HorizonBias

    mom   = _momentum_score(candles, fast=5, slow=min(20, len(candles) - 1))
    struct, struct_regime = _structure_score(candles, symbol, timeframe)
    vol_mod, vol_regime   = _volatility_conviction(candles)
    alignment             = _macro_alignment_score(
        (mom + struct) // 2, macro_score, macro_bias
    )

    # Weighted conviction (vol_mod adjusts range of outcome)
    raw = (
        0.40 * mom    +
        0.35 * struct +
        0.15 * vol_mod +
        0.10 * alignment
    )
    # Expansion amplifies, compression dampens toward 50
    if vol_regime == "expansion":
        raw = 50 + (raw - 50) * 1.15
    elif vol_regime == "compression":
        raw = 50 + (raw - 50) * 0.75

    score = _clamp(raw)
    bias  = _bias_from_score(score)
    conf  = _confidence(mom, struct, vol_mod, alignment)

    return HorizonBias(
        horizon=timeframe, timeframe_label=label,
        conviction_score=score, bias=bias, confidence=conf,
        regime=vol_regime if vol_regime in ("expansion", "compression") else struct_regime,
        drivers=_drivers(mom, struct, vol_mod, alignment, struct_regime, vol_regime),
        momentum_score=mom, structure_score=struct,
        volatility_score=vol_mod, macro_alignment=alignment,
    )
