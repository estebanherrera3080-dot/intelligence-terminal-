"""
MacroTrend indicators — pure functions, no side effects.
All inputs are lists of floats (price series), outputs are floats 0-100 or regime strings.
"""

from typing import List


# ──────────────────────────────────────────────────────────────────
#  Primitives
# ──────────────────────────────────────────────────────────────────

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> int:
    return int(max(lo, min(hi, value)))


def _momentum(prices: List[float], window: int = 20) -> float:
    """% change from `window` bars ago to now. Returns 0 if not enough data."""
    if len(prices) < window + 1:
        return 0.0
    base = prices[-window - 1]
    if base == 0:
        return 0.0
    return (prices[-1] - base) / base * 100


def _zscore(value: float, series: List[float]) -> float:
    """Normalised distance from mean (σ units). Clamped to [-3, 3]."""
    if len(series) < 2:
        return 0.0
    mean = sum(series) / len(series)
    variance = sum((x - mean) ** 2 for x in series) / len(series)
    std = variance ** 0.5
    if std == 0:
        return 0.0
    return max(-3.0, min(3.0, (value - mean) / std))


def _linear_map(value: float, in_lo: float, in_hi: float,
                out_lo: float = 0.0, out_hi: float = 100.0) -> float:
    """Map `value` from [in_lo, in_hi] to [out_lo, out_hi]."""
    if in_hi == in_lo:
        return (out_lo + out_hi) / 2
    t = (value - in_lo) / (in_hi - in_lo)
    t = max(0.0, min(1.0, t))
    return out_lo + t * (out_hi - out_lo)


# ──────────────────────────────────────────────────────────────────
#  Component Scorers  (0-100, higher = more bullish for gold)
# ──────────────────────────────────────────────────────────────────

def score_dxy(dxy_current: float, dxy_series: List[float]) -> int:
    """
    Dollar weakness score.
    Strong DXY (>106) → bearish gold → low score.
    Weak  DXY (<98)  → bullish gold → high score.
    Adds momentum component: DXY falling despite being high → partial relief.
    """
    # Level component (70% weight)
    level_score = _linear_map(dxy_current, in_lo=110, in_hi=94,
                              out_lo=0, out_hi=100)    # inverted: lower DXY = higher score

    # Momentum component (30% weight) — falling DXY is bullish for gold
    mom = _momentum(dxy_series, window=min(20, len(dxy_series) - 1))
    mom_score = _linear_map(-mom, in_lo=-3.0, in_hi=3.0, out_lo=0, out_hi=100)

    combined = 0.70 * level_score + 0.30 * mom_score
    return _clamp(combined)


def score_yield_curve(us10y: float, us02y: float) -> int:
    """
    Yield curve signal.
    Deep inversion (<-1.0%)  → recession fear → bullish gold.
    Normal steepening (>+1%) → growth → bearish gold.
    """
    spread = us10y - us02y          # positive = normal, negative = inverted
    score = _linear_map(spread, in_lo=1.5, in_hi=-2.0,
                        out_lo=0, out_hi=100)           # inverted: flatter/more inv = higher score
    return _clamp(score)


def score_real_rates(us10y: float, us10y_series: List[float]) -> int:
    """
    Real-rates proxy (nominal US10Y as stand-in until CPI module is available).
    Low nominal rates → likely negative real rates → bullish gold.
    High rates → positive real rates → opportunity cost → bearish gold.
    """
    level_score = _linear_map(us10y, in_lo=6.0, in_hi=0.5,
                              out_lo=0, out_hi=100)     # inverted: lower rate = higher score

    mom = _momentum(us10y_series, window=min(20, len(us10y_series) - 1))
    # Rising rates = bearish gold; add momentum penalty
    mom_score = _linear_map(-mom, in_lo=-1.5, in_hi=1.5, out_lo=0, out_hi=100)

    combined = 0.65 * level_score + 0.35 * mom_score
    return _clamp(combined)


def score_vix(vix_current: float) -> int:
    """
    Fear / safe-haven demand.
    VIX >30 → crisis, gold safe-haven bid → high score.
    VIX <14 → complacency → low score.
    """
    score = _linear_map(vix_current, in_lo=10, in_hi=40,
                        out_lo=20, out_hi=100)
    return _clamp(score)


def score_spx_momentum(spx_series: List[float]) -> int:
    """
    Equity stress signal — falling equities → risk-off → safe-haven gold bid.
    SPX falling hard → high score (bullish gold).
    SPX rallying → low score (risk-on, gold less needed).
    """
    mom = _momentum(spx_series, window=min(20, len(spx_series) - 1))
    score = _linear_map(-mom, in_lo=-8.0, in_hi=5.0, out_lo=10, out_hi=95)
    return _clamp(score)


def score_gold_momentum(gold_series: List[float]) -> int:
    """
    Gold's own trend as confirmation signal.
    Trend-following overlay: rising gold adds confidence to bullish bias.
    """
    mom = _momentum(gold_series, window=min(20, len(gold_series) - 1))
    score = _linear_map(mom, in_lo=-5.0, in_hi=5.0, out_lo=10, out_hi=90)
    return _clamp(score)


# ──────────────────────────────────────────────────────────────────
#  Aggregate Scores
# ──────────────────────────────────────────────────────────────────

MACRO_WEIGHTS = {
    "dxy":          0.25,
    "yield_curve":  0.20,
    "real_rates":   0.20,
    "vix_fear":     0.15,
    "spx_momentum": 0.12,
    "gold_momentum": 0.08,
}

assert abs(sum(MACRO_WEIGHTS.values()) - 1.0) < 1e-9, "Macro weights must sum to 1.0"


def compute_macro_score(components: dict) -> int:
    """Weighted average of component scores → Macro Score 0-100."""
    total = sum(components[k] * w for k, w in MACRO_WEIGHTS.items())
    return _clamp(total)


def compute_risk_score(vix: float, yield_spread: float, spx_mom: float) -> int:
    """
    Systemic risk score 0-100 (higher = more fear / systemic stress).
    Distinct from macro_score: risk_score measures market stress, not gold drivers.
    """
    vix_risk     = _linear_map(vix,           in_lo=10,  in_hi=40,  out_lo=0,  out_hi=100)
    curve_risk   = _linear_map(-yield_spread,  in_lo=-0.5, in_hi=2.5, out_lo=0,  out_hi=100)
    equity_risk  = _linear_map(-spx_mom,       in_lo=-5.0, in_hi=5.0, out_lo=0,  out_hi=100)

    combined = 0.45 * vix_risk + 0.30 * curve_risk + 0.25 * equity_risk
    return _clamp(combined)


# ──────────────────────────────────────────────────────────────────
#  Regime Classifiers
# ──────────────────────────────────────────────────────────────────

def classify_market_regime(vix: float, spx_mom: float, dxy_mom: float) -> str:
    """risk_on | risk_off | transitional"""
    if vix < 16 and spx_mom > 1.0:
        return "risk_on"
    if vix > 25 or spx_mom < -3.0:
        return "risk_off"
    return "transitional"


def classify_macro_regime(
    us10y: float,
    us02y: float,
    us10y_mom: float,
    dxy_mom: float,
    vix: float,
    spx_mom: float,
) -> str:
    """
    hawkish_fed | dovish_fed | inflationary | deflationary |
    recession_risk | growth_expansion | neutral
    """
    spread = us10y - us02y

    if spread < -0.75 and vix > 20:
        return "recession_risk"
    if us10y_mom > 0.15 and us02y > 4.5 and dxy_mom > 0.5:
        return "hawkish_fed"
    if us10y_mom < -0.10 and dxy_mom < -0.5:
        return "dovish_fed"
    if vix < 15 and spx_mom > 2.0 and spread > 0.3:
        return "growth_expansion"
    if spread < -0.5:
        return "recession_risk"
    return "neutral"


def classify_liquidity(us10y: float, vix: float, dxy: float) -> str:
    """abundant | normal | tight"""
    if us10y < 3.0 and vix < 18:
        return "abundant"
    if us10y > 5.0 or vix > 28 or dxy > 108:
        return "tight"
    return "normal"


def classify_gold_bias(macro_score: int, risk_score: int) -> str:
    """bullish | neutral | bearish"""
    if macro_score >= 62:
        return "bullish"
    if macro_score <= 38:
        return "bearish"
    return "neutral"


def compute_confidence(components: dict, macro_score: int) -> float:
    """
    Confidence = consistency of component signals.
    All pointing same direction → high confidence.
    Mixed signals → low confidence.
    """
    scores = list(components.values())
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std = variance ** 0.5

    # Low dispersion around mean = high agreement = high confidence
    agreement = _linear_map(std, in_lo=25, in_hi=0, out_lo=40, out_hi=95)

    # Stronger macro score extremes also warrant higher confidence
    extremity = abs(macro_score - 50) / 50 * 30   # 0-30 bonus

    return round(min(98.0, agreement + extremity), 1)


# ──────────────────────────────────────────────────────────────────
#  Signal Generation
# ──────────────────────────────────────────────────────────────────

def generate_signals(
    dxy_score: int,
    yield_curve_score: int,
    real_rates_score: int,
    vix_score: int,
    spx_score: int,
    yield_spread: float,
    vix: float,
    us10y: float,
    dxy: float,
    spx_mom: float,
) -> tuple[list[str], list[str]]:
    """Return (key_signals, risk_factors)."""
    signals: list[str] = []
    risks: list[str] = []

    if yield_spread < -0.5:
        signals.append(f"Yield curve inverted ({yield_spread:+.2f}%) — recession signal")
    elif yield_spread > 1.0:
        signals.append(f"Yield curve steepening ({yield_spread:+.2f}%) — growth signal")

    if vix > 25:
        signals.append(f"VIX elevated ({vix:.1f}) — safe-haven demand for gold")
    elif vix < 14:
        risks.append(f"VIX compressed ({vix:.1f}) — complacency, gold less bid")

    if us10y > 5.0:
        risks.append(f"10Y yield at {us10y:.2f}% — high opportunity cost for gold")
    elif us10y < 2.5:
        signals.append(f"10Y yield low ({us10y:.2f}%) — supportive real rates for gold")

    if dxy > 106:
        risks.append(f"DXY strong ({dxy:.1f}) — dollar headwind for gold")
    elif dxy < 100:
        signals.append(f"DXY weak ({dxy:.1f}) — dollar tailwind for gold")

    if spx_mom < -3.0:
        signals.append(f"S&P 500 selling off ({spx_mom:+.1f}%) — flight to safety")
    elif spx_mom > 3.0:
        risks.append(f"S&P 500 rallying ({spx_mom:+.1f}%) — risk-on, gold competition")

    return signals, risks


def generate_scenarios(gold_bias: str, macro_regime: str, market_regime: str) -> tuple[str, str]:
    """Return (primary_scenario, alternate_scenario)."""
    scenarios = {
        ("bullish", "recession_risk", "risk_off"): (
            "Flight-to-safety rally — recession fears drive institutional gold buying",
            "Risk stabilizes → partial gold giveback as equities recover",
        ),
        ("bullish", "dovish_fed", "transitional"): (
            "Fed pivot narrative supports gold via weaker real rates and DXY",
            "Fed stays higher-for-longer → rate headwinds cap upside",
        ),
        ("bullish", "hawkish_fed", "transitional"): (
            "Stagflationary environment — gold bid despite rate pressure",
            "Fed succeeds in cooling inflation → normalization bearish for gold",
        ),
        ("bearish", "growth_expansion", "risk_on"): (
            "Risk-on rotation out of gold into equities and risk assets",
            "Growth momentum stalls → safe-haven demand returns",
        ),
        ("bearish", "hawkish_fed", "risk_on"): (
            "Strong dollar + high real rates erode gold's appeal",
            "Hard landing risk materializes → rapid gold reversal",
        ),
        ("neutral", "neutral", "transitional"): (
            "Macro uncertainty — gold consolidates awaiting directional catalyst",
            "Either a Fed pivot or growth shock breaks the range",
        ),
    }

    key = (gold_bias, macro_regime, market_regime)
    primary, alternate = scenarios.get(
        key,
        (
            f"Gold bias {gold_bias} under {macro_regime} / {market_regime} conditions",
            "Monitor yield curve and DXY for next directional signal",
        ),
    )
    return primary, alternate
