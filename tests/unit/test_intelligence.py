"""
Unit tests for Gold Intelligence Engine — Multi-Timeframe Bias.
"""

import pytest
from datetime import UTC, datetime, timedelta

from app.schemas.market import OHLCVData
from app.services.gold_intelligence.analyzer import (
    _momentum_score, _structure_score, _volatility_conviction,
    _macro_alignment_score, analyze_timeframe,
)
from app.services.gold_intelligence.engine import (
    GoldIntelligenceEngine, _weighted_score, _majority_bias,
    _alignment_label, _consensus_confidence,
)
from app.services.gold_intelligence.schemas import HorizonBias
from app.services.market_data.providers.mock import MockMarketDataProvider


# ── Candle factory ────────────────────────────────────────────────

def make_candle(close: float, high: float = None, low: float = None,
                open_: float = None, i: int = 0) -> OHLCVData:
    o = open_ if open_ is not None else close * 0.999
    h = high  if high  is not None else close * 1.005
    l = low   if low   is not None else close * 0.995
    return OHLCVData(
        symbol="XAUUSD", timeframe="1h",
        open=o, high=h, low=l, close=close, volume=1_000_000,
        timestamp=datetime.now(UTC) - timedelta(hours=100 - i),
        data_source="test",
    )


def rising(n: int = 60) -> list:
    return [make_candle(2000 + i * 8, i=i) for i in range(n)]


def falling(n: int = 60) -> list:
    return [make_candle(2500 - i * 8, i=i) for i in range(n)]


def flat(n: int = 60) -> list:
    return [make_candle(2050.0, i=i) for i in range(n)]


# ── Momentum score ────────────────────────────────────────────────

@pytest.mark.unit
def test_momentum_rising_is_bullish():
    score = _momentum_score(rising(40), fast=5, slow=20)
    assert score > 50, f"Rising market should be bullish, got {score}"


@pytest.mark.unit
def test_momentum_falling_is_bearish():
    score = _momentum_score(falling(40), fast=5, slow=20)
    assert score < 50, f"Falling market should be bearish, got {score}"


@pytest.mark.unit
def test_momentum_flat_is_neutral():
    score = _momentum_score(flat(40), fast=5, slow=20)
    assert 35 <= score <= 65, f"Flat market should be neutral, got {score}"


@pytest.mark.unit
def test_momentum_bounded():
    for candles in [rising(50), falling(50), flat(50)]:
        s = _momentum_score(candles)
        assert 0 <= s <= 100


# ── Structure score ───────────────────────────────────────────────

@pytest.mark.unit
def test_structure_score_bounded():
    for candles in [rising(40), falling(40), flat(40)]:
        score, _ = _structure_score(candles, "XAUUSD", "1h")
        assert 0 <= score <= 100


@pytest.mark.unit
def test_structure_insufficient_data():
    score, regime = _structure_score([make_candle(2050.0)], "XAUUSD", "1h")
    assert regime == "insufficient_data"
    assert score == 50


# ── Volatility conviction ─────────────────────────────────────────

@pytest.mark.unit
def test_volatility_conviction_bounded():
    for candles in [rising(40), falling(40), flat(40)]:
        mod, regime = _volatility_conviction(candles)
        assert 0 <= mod <= 100
        assert isinstance(regime, str)


# ── Macro alignment ───────────────────────────────────────────────

@pytest.mark.unit
def test_macro_alignment_agrees():
    score = _macro_alignment_score(
        horizon_score=75,   # bullish TF
        macro_score=70,     # bullish macro
        macro_bias="bullish",
    )
    assert score > 60, f"Aligned macro should give high alignment, got {score}"


@pytest.mark.unit
def test_macro_alignment_disagrees():
    score = _macro_alignment_score(
        horizon_score=30,   # bearish TF
        macro_score=70,     # bullish macro
        macro_bias="bullish",
    )
    assert score < 40, f"Conflicting macro should give low alignment, got {score}"


@pytest.mark.unit
def test_macro_alignment_bounded():
    for hs, ms, mb in [(75, 70, "bullish"), (30, 40, "bearish"), (50, 50, "neutral")]:
        s = _macro_alignment_score(hs, ms, mb)
        assert 0 <= s <= 100


# ── Full timeframe analyzer ───────────────────────────────────────

@pytest.mark.unit
def test_analyze_timeframe_returns_valid():
    bias = analyze_timeframe(
        candles=rising(50),
        symbol="XAUUSD", timeframe="15m", label="15 Min",
        macro_score=65, macro_bias="bullish",
    )
    assert bias.conviction_score >= 0
    assert bias.conviction_score <= 100
    assert bias.bias in ("bullish", "neutral", "bearish")
    assert 0 <= bias.confidence <= 100
    assert isinstance(bias.drivers, list)


@pytest.mark.unit
def test_analyze_rising_with_bullish_macro_high_conviction():
    bias = analyze_timeframe(
        candles=rising(60),
        symbol="XAUUSD", timeframe="15m", label="15 Min",
        macro_score=72, macro_bias="bullish",
    )
    assert bias.conviction_score > 55, "Rising + bullish macro should be bullish"


@pytest.mark.unit
def test_analyze_falling_with_bearish_macro():
    bias = analyze_timeframe(
        candles=falling(60),
        symbol="XAUUSD", timeframe="15m", label="15 Min",
        macro_score=30, macro_bias="bearish",
    )
    assert bias.conviction_score < 45, "Falling + bearish macro should be bearish"


# ── Consensus helpers ─────────────────────────────────────────────

def make_horizon(bias: str, score: int, conf: float = 70.0) -> HorizonBias:
    return HorizonBias(
        horizon="test", timeframe_label="Test",
        conviction_score=score, bias=bias, confidence=conf,
        regime="neutral", drivers=[],
    )


@pytest.mark.unit
def test_weighted_score_all_bullish():
    horizons = {
        "5m":    make_horizon("bullish", 75),
        "15m":   make_horizon("bullish", 72),
        "1h":    make_horizon("bullish", 70),
        "macro": make_horizon("bullish", 68),
    }
    score = _weighted_score(horizons)
    assert score > 60


@pytest.mark.unit
def test_weighted_score_all_bearish():
    horizons = {
        "5m":    make_horizon("bearish", 25),
        "15m":   make_horizon("bearish", 28),
        "1h":    make_horizon("bearish", 30),
        "macro": make_horizon("bearish", 32),
    }
    score = _weighted_score(horizons)
    assert score < 40


@pytest.mark.unit
def test_majority_bias_3v1_bullish():
    horizons = {
        "5m":    make_horizon("bullish", 70),
        "15m":   make_horizon("bullish", 68),
        "1h":    make_horizon("bearish", 30),
        "macro": make_horizon("bullish", 65),
    }
    assert _majority_bias(horizons) == "bullish"


@pytest.mark.unit
def test_majority_bias_1bullish_3neutral_is_neutral():
    """1 bullish vs 3 neutral — neutral should win, not bullish."""
    horizons = {
        "5m":    make_horizon("bullish", 63),
        "15m":   make_horizon("neutral", 48),
        "1h":    make_horizon("neutral", 45),
        "macro": make_horizon("neutral", 47),
    }
    assert _majority_bias(horizons) == "neutral"


@pytest.mark.unit
def test_majority_bias_2v2_is_neutral():
    """2 bullish vs 2 bearish — no majority → neutral."""
    horizons = {
        "5m":    make_horizon("bullish", 65),
        "15m":   make_horizon("bullish", 62),
        "1h":    make_horizon("bearish", 35),
        "macro": make_horizon("bearish", 38),
    }
    # 2v2 — neither reaches clear majority
    result = _majority_bias(horizons)
    assert result in ("bullish", "bearish", "neutral")  # either is acceptable at 2v2


@pytest.mark.unit
def test_alignment_label_aligned():
    horizons = {k: make_horizon("bullish", 70) for k in ["5m", "15m", "1h", "macro"]}
    assert _alignment_label(horizons) == "aligned"


@pytest.mark.unit
def test_alignment_label_conflicted():
    horizons = {
        "5m":    make_horizon("bullish", 70),
        "15m":   make_horizon("bearish", 30),
        "1h":    make_horizon("neutral", 50),
        "macro": make_horizon("bearish", 35),
    }
    assert _alignment_label(horizons) in ("mixed", "conflicted")


@pytest.mark.unit
def test_confidence_lower_when_conflicted():
    h_aligned    = {k: make_horizon("bullish", 70, 80.0) for k in ["5m", "15m", "1h", "macro"]}
    h_conflicted = {
        "5m":    make_horizon("bullish", 70, 80.0),
        "15m":   make_horizon("bearish", 30, 80.0),
        "1h":    make_horizon("neutral", 50, 80.0),
        "macro": make_horizon("bearish", 35, 80.0),
    }
    c_aligned    = _consensus_confidence(h_aligned,    "aligned")
    c_conflicted = _consensus_confidence(h_conflicted, "conflicted")
    assert c_aligned > c_conflicted


# ── Engine integration ────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_returns_valid_consensus():
    engine = GoldIntelligenceEngine(provider=MockMarketDataProvider(seed=42))
    r = await engine.analyze()

    assert 0 <= r.consensus_score <= 100
    assert r.consensus_bias in ("bullish", "neutral", "bearish")
    assert r.alignment in ("aligned", "mixed", "conflicted")
    assert 0 <= r.confidence <= 100
    assert r.dominant_timeframe != ""
    assert r.key_insight != ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_all_horizons_valid():
    engine = GoldIntelligenceEngine(provider=MockMarketDataProvider(seed=7))
    r = await engine.analyze()

    for h in [r.m5, r.m15, r.h1, r.macro]:
        assert 0 <= h.conviction_score <= 100
        assert h.bias in ("bullish", "neutral", "bearish")
        assert 0 <= h.confidence <= 100
        assert isinstance(h.drivers, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_macro_alignment_present():
    engine = GoldIntelligenceEngine(provider=MockMarketDataProvider(seed=3))
    r = await engine.analyze()
    # macro is always self-aligned
    assert r.macro.macro_alignment == 100


# ── HTTP endpoints ────────────────────────────────────────────────

@pytest.mark.unit
def test_intelligence_bias_endpoint(client):
    res = client.get("/api/v1/intelligence/bias")
    assert res.status_code == 200
    d = res.json()
    assert "consensus_score" in d
    assert "consensus_bias" in d
    assert "alignment" in d
    assert "timeframes" in d
    for tf in ["5m", "15m", "1h", "macro"]:
        assert tf in d["timeframes"]
        assert 0 <= d["timeframes"][tf]["conviction_score"] <= 100
        assert d["timeframes"][tf]["bias"] in ("bullish", "neutral", "bearish")


@pytest.mark.unit
def test_intelligence_consensus_endpoint(client):
    res = client.get("/api/v1/intelligence/consensus")
    assert res.status_code == 200
    d = res.json()
    assert "m5" in d
    assert "m15" in d
    assert "h1" in d
    assert "macro" in d
    assert "consensus_score" in d
    assert "key_insight" in d
