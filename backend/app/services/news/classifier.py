"""
News sentiment classifier — keyword-based Fed language analysis.

Classifies text as HAWKISH / NEUTRAL / DOVISH and assigns:
  - impact_score  0-100 (market significance)
  - gold_impact   bullish | neutral | bearish
  - confidence    0-100%

Fed language key:
  Hawkish → rates up / inflation fighting → bearish for gold
  Dovish  → rates down / growth support  → bullish for gold
"""

import re
from typing import List, Tuple

# ── Hawkish vocabulary (Fed tightening bias) ───────────────────────
_HAWKISH = [
    "tighten", "tightening", "raise rates", "rate hike", "rate increase",
    "restrictive", "above target", "inflation elevated", "above 2%",
    "not premature", "higher for longer", "remain elevated",
    "not appropriate to cut", "not appropriate to reduce",
    "vigilant", "persistent inflation", "strong labor market", "robust employment",
    "overheating", "upside risks to inflation", "continue to monitor",
    "additional increases", "further tightening", "not considering cuts",
    "inflation not sustainably", "above neutral",
    "not enough progress", "too soon to cut",
    "sticky inflation", "hawkish", "normalize policy",
    "maintain restrictive", "maintain the current rate",
    "hold rates", "rates sufficiently restrictive",
    "not yet confident", "need more evidence",
]

# ── Dovish vocabulary (Fed easing bias) ───────────────────────────
_DOVISH = [
    # Use longer, more specific phrases to avoid false matches inside negations
    "will cut rates", "begin cutting rates", "start cutting rates",
    "rate cut is appropriate", "appropriate to reduce rates",
    "lower interest rates", "easing monetary policy", "ease policy",
    "accommodative policy", "below target inflation", "inflation falling",
    "disinflation", "slower growth", "labor market cooling",
    "rising unemployment", "recession risk", "downside risks to growth",
    "dovish", "overly restrictive policy",
    "inflation sustainably at 2", "inflation returned to 2 percent",
    "progress made on inflation", "appropriate to cut",
    "soft landing achieved", "cooling inflation trend",
    "labor market softening significantly", "slowing economy warrants",
    "consider reducing", "time to ease", "pivot to easing",
    "pause hiking", "halt rate increases",
]

# ── Neutral / uncertainty vocabulary ─────────────────────────────
_NEUTRAL = [
    "data dependent", "meeting by meeting", "wait and see", "monitor closely",
    "assess incoming data", "appropriate level", "gradual approach",
    "cautious", "balanced approach", "uncertainty", "two-sided risks",
]

# ── Event type base impact scores ────────────────────────────────
_BASE_IMPACT = {
    "FOMC":        90,
    "POWELL":      85,
    "CPI":         85,
    "NFP":         80,
    "PCE":         78,
    "FED_SPEAKER": 55,
    "TREASURY":    50,
    "GDP":         70,
    "RETAIL_SALES": 55,
    "ISM":         50,
    "OTHER":       30,
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _count_matches(text: str, keywords: List[str]) -> Tuple[int, float]:
    """Returns (count, weighted_score) — longer phrases weighted more."""
    n = text_lower = text.lower()
    count = 0
    weight = 0.0
    for kw in keywords:
        occurrences = text_lower.count(kw)
        if occurrences:
            count += occurrences
            weight += occurrences * (1 + len(kw.split()) * 0.3)
    return count, weight


def classify_text(text: str, event_type: str = "OTHER") -> dict:
    """
    Classify raw text and return sentiment + scores.

    Returns:
        sentiment:    hawkish | neutral | dovish
        impact_score: 0-100
        gold_impact:  bullish | neutral | bearish
        confidence:   0-100%
        hawkish_score: raw score
        dovish_score:  raw score
    """
    t = _normalize(text)

    _, h_score = _count_matches(t, _HAWKISH)
    _, d_score = _count_matches(t, _DOVISH)
    _, n_score = _count_matches(t, _NEUTRAL)

    total = h_score + d_score + n_score + 1e-9

    # Sentiment score: 0 = max dovish, 50 = neutral, 100 = max hawkish
    fed_score = int(50 + (h_score - d_score) / total * 50)
    fed_score = max(0, min(100, fed_score))

    # Classification (60 threshold — slightly relaxed from 62)
    if fed_score >= 60:
        sentiment = "hawkish"
        gold_impact = "bearish"   # hawkish Fed = bearish gold
    elif fed_score <= 38:
        sentiment = "dovish"
        gold_impact = "bullish"   # dovish Fed = bullish gold
    else:
        sentiment = "neutral"
        gold_impact = "neutral"

    # Confidence: how decisive the signal is
    signal_strength = abs(h_score - d_score) / total
    confidence = round(min(95.0, 40 + signal_strength * 80), 1)

    # Impact score: event type base + sentiment extremity
    base = _BASE_IMPACT.get(event_type, 30)
    extremity_bonus = abs(fed_score - 50) * 0.3
    impact_score = int(min(100, base + extremity_bonus))

    return {
        "sentiment":     sentiment,
        "fed_score":     fed_score,
        "gold_impact":   gold_impact,
        "confidence":    confidence,
        "impact_score":  impact_score,
        "hawkish_score": round(h_score, 2),
        "dovish_score":  round(d_score, 2),
    }


def classify_economic_release(
    event_type: str,
    actual: float,
    forecast: float,
    previous: float,
) -> dict:
    """
    Classify an economic data release (CPI, NFP, PCE, GDP) by surprise direction.

    Surprise logic for gold:
      CPI/PCE above forecast → hawkish → bearish gold (inflation = more hikes)
      NFP above forecast     → hawkish → bearish gold (hot labor = no cuts)
      GDP above forecast     → hawkish → bearish gold (strong economy)
      Any below forecast     → dovish  → bullish gold
    """
    if forecast == 0:
        surprise_pct = 0.0
    else:
        surprise_pct = (actual - forecast) / abs(forecast) * 100

    # Events where beat = hawkish
    hawkish_if_beat = {"CPI", "PCE", "NFP", "ISM"}
    # Events where beat = dovish (GDP miss = recession risk → gold bullish)
    dovish_if_beat = {"UNEMPLOYMENT_RATE"}

    is_beat = actual > forecast

    if event_type in hawkish_if_beat:
        hawkish = is_beat
    elif event_type in dovish_if_beat:
        hawkish = not is_beat
    else:
        hawkish = is_beat   # default: beat = hawkish

    abs_surprise = abs(surprise_pct)
    if abs_surprise < 0.5:
        sentiment = "neutral"
        gold_impact = "neutral"
    elif hawkish:
        sentiment = "hawkish"
        gold_impact = "bearish"
    else:
        sentiment = "dovish"
        gold_impact = "bullish"

    base = _BASE_IMPACT.get(event_type, 50)
    impact_score = int(min(100, base + abs_surprise * 2))
    confidence = round(min(95.0, 50 + abs_surprise * 5), 1)

    return {
        "sentiment":     sentiment,
        "gold_impact":   gold_impact,
        "impact_score":  impact_score,
        "confidence":    confidence,
        "surprise_pct":  round(surprise_pct, 2),
        "fed_score":     75 if sentiment == "hawkish" else (25 if sentiment == "dovish" else 50),
    }


def aggregate_fed_stance(events: list) -> Tuple[str, int, float]:
    """
    Weighted average of recent events → Fed stance + score.
    More recent events weighted higher.
    """
    if not events:
        return "neutral", 50, 50.0

    # Weight by impact_score and recency (index = older → lower weight)
    total_weight = 0.0
    weighted_score = 0.0
    total_confidence = 0.0

    for i, ev in enumerate(events[-10:]):  # last 10 events max
        recency_w = (i + 1) / 10         # 0.1 to 1.0
        impact_w  = ev.impact_score / 100
        w = recency_w * impact_w
        weighted_score    += ev.impact_score * w  # reuse fed_score if stored
        total_weight      += w
        total_confidence  += ev.confidence * w

    if total_weight == 0:
        return "neutral", 50, 50.0

    # Re-derive score from event sentiments
    hawkish_w = sum(
        ev.impact_score * ((i + 1) / 10) / 100
        for i, ev in enumerate(events[-10:]) if ev.sentiment == "hawkish"
    )
    dovish_w = sum(
        ev.impact_score * ((i + 1) / 10) / 100
        for i, ev in enumerate(events[-10:]) if ev.sentiment == "dovish"
    )
    total_w = hawkish_w + dovish_w + 1e-9

    fed_score = int(50 + (hawkish_w - dovish_w) / total_w * 40)
    fed_score = max(0, min(100, fed_score))
    confidence = round(total_confidence / total_weight, 1)

    if fed_score >= 60:
        stance = "hawkish"
    elif fed_score <= 40:
        stance = "dovish"
    else:
        stance = "neutral"

    return stance, fed_score, confidence
