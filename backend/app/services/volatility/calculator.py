"""
Volatility Engine — pure calculation functions.

All inputs are lists of OHLCVData (chronological, oldest first).
All outputs are plain Python scalars — no external dependencies.
"""

import math
from typing import List, Tuple

from app.schemas.market import OHLCVData


# ── Primitives ────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def _zscore(value: float, values: List[float]) -> float:
    s = _std(values)
    if s == 0:
        return 0.0
    return _clamp((value - _mean(values)) / s, -3.0, 3.0)


def _annualize(vol_pct: float, periods_per_year: int = 252) -> float:
    """Annualize a per-period std dev. Input is already in % form."""
    return vol_pct * math.sqrt(periods_per_year)


# ── True Range ────────────────────────────────────────────────────

def true_range(candle: OHLCVData, prev_close: float) -> float:
    """TR = max(H-L, |H-PC|, |L-PC|)"""
    return max(
        candle.high - candle.low,
        abs(candle.high - prev_close),
        abs(candle.low  - prev_close),
    )


def compute_atr(candles: List[OHLCVData], period: int = 14) -> List[float]:
    """Wilder's ATR via exponential smoothing."""
    if len(candles) < 2:
        return []
    trs = [true_range(candles[i], candles[i - 1].close) for i in range(1, len(candles))]
    if not trs:
        return []

    atr_vals: List[float] = [_mean(trs[:period])]
    k = 1.0 / period
    for tr in trs[period:]:
        atr_vals.append(atr_vals[-1] * (1 - k) + tr * k)
    return atr_vals


# ── Realized Volatility ───────────────────────────────────────────

def realized_vol(candles: List[OHLCVData], window: int = 20) -> float:
    """
    Annualized realized volatility from log returns.
    Returns 0.0 if not enough data.
    """
    if len(candles) < window + 1:
        return 0.0
    tail = candles[-(window + 1):]
    log_returns = [
        math.log(tail[i].close / tail[i - 1].close)
        for i in range(1, len(tail))
        if tail[i - 1].close > 0 and tail[i].close > 0
    ]
    if len(log_returns) < 2:
        return 0.0
    daily_std = _std(log_returns)
    # For 1h candles: ~6 sessions/day → 252*6 = 1512 periods/year
    # For 4h candles: ~252*1.5 = 378; 1d: 252
    return _annualize(daily_std * 100, periods_per_year=1512)


# ── Range Analysis ────────────────────────────────────────────────

def candle_range_pct(c: OHLCVData) -> float:
    return (c.high - c.low) / c.close * 100 if c.close > 0 else 0.0


def body_ratio(c: OHLCVData) -> float:
    total_range = c.high - c.low
    if total_range == 0:
        return 0.0
    return abs(c.close - c.open) / total_range


def avg_range_pct(candles: List[OHLCVData], window: int = 20) -> float:
    if not candles:
        return 0.0
    tail = candles[-window:]
    return _mean([candle_range_pct(c) for c in tail])


# ── Regime Classification ─────────────────────────────────────────

def classify_vol_regime(
    atr_pct: float,
    atr_zscore: float,
    realized_20: float,
    range_compression: float,
) -> Tuple[str, float, float, float]:
    """
    Returns (regime, vol_score, compression_score, expansion_score).

    Regime labels:
      compression  — ATR below average, tight ranges, coiling
      low          — calm, below-normal volatility
      medium       — normal environment
      high         — elevated volatility
      expansion    — ATR spiking above average, breakout energy
    """
    # Vol score 0-100 (higher = more volatile)
    vol_score = _clamp(
        50 + atr_zscore * 15 + (atr_pct - 0.5) * 10
    )

    # Compression score 0-100 (higher = more compressed, coiling for breakout)
    compression_score = _clamp(100 - vol_score * 0.8 + (1 - range_compression) * 30)

    # Expansion score 0-100 (higher = breakout/expansion energy)
    expansion_score = _clamp(
        vol_score * 0.6 + max(0, atr_zscore) * 20
    )

    # Regime label
    if range_compression < 0.6 and atr_zscore < -0.5:
        regime = "compression"
    elif vol_score < 35:
        regime = "low"
    elif vol_score > 72:
        if atr_zscore > 1.0:
            regime = "expansion"
        else:
            regime = "high"
    elif atr_zscore > 1.5:
        regime = "expansion"
    else:
        regime = "medium"

    return regime, round(vol_score, 1), round(compression_score, 1), round(expansion_score, 1)


def classify_vix_regime(vix: float) -> str:
    if vix < 13:
        return "low"
    if vix < 20:
        return "normal"
    if vix < 30:
        return "elevated"
    return "spike"


def classify_market_vol_regime(vix: float, gold_atr_pct: float) -> str:
    if vix < 14 and gold_atr_pct < 0.4:
        return "calm"
    if vix > 28 or gold_atr_pct > 1.2:
        return "extreme"
    if vix > 20 or gold_atr_pct > 0.8:
        return "elevated"
    return "normal"


# ── Signal Generation ─────────────────────────────────────────────

def generate_vol_signals(
    regime: str,
    atr_pct: float,
    atr_zscore: float,
    range_compression: float,
    realized_20: float,
    body_ratio_val: float,
) -> List[str]:
    signals = []

    if regime == "compression":
        signals.append(f"Volatility compression (ATR z={atr_zscore:.1f}) - breakout likely")
    if regime == "expansion":
        signals.append(f"Volatility expansion - ATR {atr_pct:.2f}% of price, trending move")
    if range_compression < 0.5:
        signals.append("Candle ranges tightening - energy coiling for directional move")
    if atr_zscore > 2.0:
        signals.append(f"ATR at {atr_zscore:.1f}s above average - abnormal volatility, widen stops")
    if body_ratio_val < 0.25:
        signals.append("Doji / indecision candles - market in equilibrium, await catalyst")
    if realized_20 > 20:
        signals.append(f"Realized vol elevated ({realized_20:.1f}% ann.) - institutional activity")

    return signals
