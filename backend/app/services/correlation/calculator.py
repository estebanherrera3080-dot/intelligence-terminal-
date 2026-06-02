"""
Correlation Engine — pure calculation functions.
Inputs: price series (List[float], chronological).
"""

import math
from typing import Dict, List, Optional, Tuple

from app.services.correlation.schemas import (
    BreakdownEvent, GoldCorrelationProfile, PairCorrelation,
)
from datetime import UTC, datetime


# ── Canonical correlations (institutional priors) ─────────────────
# Expected Pearson correlation of each symbol WITH GOLD (XAUUSD)
# Based on multi-decade empirical relationships.
GOLD_EXPECTED_CORR: Dict[str, float] = {
    "DXY":   -0.65,   # strong negative: weak dollar = bullish gold
    "US10Y": -0.40,   # negative: high real rates = bearish gold
    "US02Y": -0.35,   # similar to 10Y but shorter duration
    "SPX":   -0.10,   # near-zero in normal regimes, negative in crisis
    "NDX":   -0.08,
    "VIX":   +0.45,   # positive: fear spikes drive safe-haven gold buying
}

# Breakdown thresholds
_BREAKDOWN_Z    = 1.5    # z-score threshold for breakdown
_BREAKDOWN_DELTA = 0.25  # minimum absolute delta for breakdown


# ── Primitives ────────────────────────────────────────────────────

def _log_returns(prices: List[float]) -> List[float]:
    return [
        math.log(prices[i] / prices[i - 1])
        for i in range(1, len(prices))
        if prices[i - 1] > 0 and prices[i] > 0
    ]


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ── Pearson correlation ───────────────────────────────────────────

def pearson(x: List[float], y: List[float]) -> float:
    """
    Pearson correlation of two equal-length series.
    Returns 0.0 if series are constant or insufficient.
    """
    n = min(len(x), len(y))
    if n < 5:
        return 0.0
    x, y = x[-n:], y[-n:]

    mx, my = _mean(x), _mean(y)
    num  = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    dx   = math.sqrt(sum((v - mx) ** 2 for v in x))
    dy   = math.sqrt(sum((v - my) ** 2 for v in y))

    if dx == 0 or dy == 0:
        return 0.0
    return _clamp(num / (dx * dy))


def rolling_correlation(
    x: List[float], y: List[float], window: int
) -> List[float]:
    """Compute rolling Pearson over `window`-period windows."""
    n = min(len(x), len(y))
    result = []
    for i in range(window, n + 1):
        result.append(pearson(x[i - window:i], y[i - window:i]))
    return result


# ── Correlation analysis for a pair ──────────────────────────────

def analyze_pair(
    sym_a: str,
    sym_b: str,
    prices_a: List[float],
    prices_b: List[float],
) -> Optional[PairCorrelation]:
    if len(prices_a) < 25 or len(prices_b) < 25:
        return None

    ret_a = _log_returns(prices_a)
    ret_b = _log_returns(prices_b)

    # Current (20-period) vs historical (50-period)
    corr_20 = pearson(ret_a[-20:], ret_b[-20:])
    corr_50 = pearson(ret_a[-50:], ret_b[-50:]) if len(ret_a) >= 50 else corr_20
    delta   = round(corr_20 - corr_50, 4)

    # Z-score of current vs rolling distribution
    roll = rolling_correlation(ret_a, ret_b, window=20)
    z = 0.0
    if len(roll) >= 10:
        m, s = _mean(roll[:-1]), _std(roll[:-1])
        z = (roll[-1] - m) / s if s > 0 else 0.0
        z = max(-4.0, min(4.0, z))

    # Direction / strength
    direction = "positive" if corr_20 > 0.1 else ("negative" if corr_20 < -0.1 else "neutral")
    abs_c = abs(corr_20)
    strength = "strong" if abs_c > 0.6 else ("moderate" if abs_c > 0.3 else ("weak" if abs_c > 0.1 else "none"))

    is_breakdown = abs(delta) >= _BREAKDOWN_DELTA and abs(z) >= _BREAKDOWN_Z

    interpretation = _interpret(sym_a, sym_b, corr_20, delta, is_breakdown)

    return PairCorrelation(
        symbol_a=sym_a, symbol_b=sym_b, pair=f"{sym_a}-{sym_b}",
        corr_current=round(corr_20, 4),
        corr_50=round(corr_50, 4),
        corr_delta=delta,
        zscore=round(z, 3),
        direction=direction, strength=strength,
        is_breakdown=is_breakdown,
        interpretation=interpretation,
    )


def _interpret(a: str, b: str, corr: float, delta: float, breakdown: bool) -> str:
    if breakdown:
        direction = "decoupling from" if abs(delta) > 0.3 else "drifting from"
        return f"{a} is {direction} {b} (delta {delta:+.2f}) - monitor for regime change"

    if a == "XAUUSD" or b == "XAUUSD":
        other = b if a == "XAUUSD" else a
        if other == "DXY":
            if corr < -0.5:
                return "Classic inverse: gold rising as dollar weakens"
            if corr > -0.2:
                return "DXY-Gold correlation weakening - possible structural shift"
        if other == "VIX":
            if corr > 0.4:
                return "Safe-haven correlation active - risk-off bid for gold"
            if corr < 0.1:
                return "VIX-Gold decoupled - gold not pricing fear premium"
        if other == "SPX":
            if corr < -0.3:
                return "Crisis correlation: gold rising as equities fall"
            if corr > 0.3:
                return "Gold and equities rising together - liquidity-driven rally"

    return f"{a}/{b} correlation: {corr:+.2f} ({('positive' if corr > 0 else 'negative')})"


# ── Breakdown events ──────────────────────────────────────────────

def detect_breakdowns(pairs: List[PairCorrelation], timestamp: datetime) -> List[BreakdownEvent]:
    events = []
    for p in pairs:
        if not p.is_breakdown:
            continue
        severity = (
            "major"    if abs(p.zscore) > 2.5 else
            "moderate" if abs(p.zscore) > 2.0 else
            "minor"
        )
        events.append(BreakdownEvent(
            pair=p.pair,
            timestamp=timestamp,
            normal_corr=p.corr_50,
            current_corr=p.corr_current,
            deviation=p.corr_delta,
            zscore=p.zscore,
            severity=severity,
            description=(
                f"{p.pair} correlation shifted {p.corr_delta:+.2f} from historical norm "
                f"({p.corr_50:+.2f} → {p.corr_current:+.2f}), z={p.zscore:.1f}"
            ),
        ))
    return sorted(events, key=lambda e: abs(e.zscore), reverse=True)


# ── Gold correlation profile ──────────────────────────────────────

def build_gold_profile(
    gold_prices: List[float],
    other_prices: Dict[str, List[float]],
    timestamp: datetime,
) -> GoldCorrelationProfile:
    ret_gold = _log_returns(gold_prices)
    current: Dict[str, float] = {}
    deviations: Dict[str, float] = {}

    for sym, prices in other_prices.items():
        if len(prices) < 20:
            continue
        ret_other = _log_returns(prices)
        c = pearson(ret_gold[-20:], ret_other[-20:])
        current[sym] = round(c, 4)
        expected = GOLD_EXPECTED_CORR.get(sym, 0.0)
        deviations[sym] = round(c - expected, 4)

    return GoldCorrelationProfile(
        timestamp=timestamp,
        xauusd_vs=current,
        expected=GOLD_EXPECTED_CORR,
        deviations=deviations,
    )


# ── Overall regime ────────────────────────────────────────────────

def classify_correlation_regime(
    pairs: List[PairCorrelation],
    breakdowns: List[BreakdownEvent],
) -> Tuple[str, float]:
    n_breakdowns = len(breakdowns)
    major = sum(1 for b in breakdowns if b.severity == "major")
    avg_z = _mean([abs(p.zscore) for p in pairs]) if pairs else 0.0

    score = min(100.0, n_breakdowns * 20 + major * 30 + avg_z * 10)

    if major >= 2 or score >= 70:
        regime = "breakdown"
    elif n_breakdowns >= 1 or score >= 35:
        regime = "stressed"
    else:
        regime = "normal"

    return regime, round(score, 1)


def dominant_signal(pairs: List[PairCorrelation], gold_profile: GoldCorrelationProfile) -> str:
    gold_dxy = gold_profile.xauusd_vs.get("DXY", 0.0)
    gold_vix = gold_profile.xauusd_vs.get("VIX", 0.0)
    gold_spx = gold_profile.xauusd_vs.get("SPX", 0.0)

    if gold_dxy < -0.6 and gold_vix > 0.4:
        return "Classic risk-off: gold bid via weak dollar + fear premium"
    if gold_dxy > -0.2:
        return "Gold-DXY correlation weakening - dollar losing influence on gold"
    if gold_spx > 0.4:
        return "Gold and equities correlated - liquidity-driven environment"
    if gold_vix < 0.1:
        return "Gold not pricing fear - safe-haven premium absent"
    return "Correlations within normal institutional ranges"
