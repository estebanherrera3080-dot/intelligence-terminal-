"""
Unit tests for MacroTrend Engine — Module 2.
All tests are fully offline (mock provider, no DB, no network).
"""

import pytest

from app.services.macro import indicators as ind
from app.services.macro.engine import MacroTrendEngine
from app.services.market_data.providers.mock import MockMarketDataProvider


# ──────────────────────────────────────────────────────────────────
#  Indicator unit tests
# ──────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_score_dxy_strong_dollar_is_low():
    """Strong DXY (bearish for gold) → low score."""
    score = ind.score_dxy(dxy_current=110.0, dxy_series=[110.0] * 25)
    assert score < 35, f"Expected low score for strong DXY, got {score}"


@pytest.mark.unit
def test_score_dxy_weak_dollar_is_high():
    """Weak DXY (bullish for gold) → high score."""
    score = ind.score_dxy(dxy_current=94.0, dxy_series=[94.0] * 25)
    assert score > 65, f"Expected high score for weak DXY, got {score}"


@pytest.mark.unit
def test_score_yield_curve_inverted_is_high():
    """Deep inversion → recession signal → bullish gold → high score."""
    score = ind.score_yield_curve(us10y=3.5, us02y=5.5)   # -2.0 spread
    assert score > 70, f"Expected high score for inverted curve, got {score}"


@pytest.mark.unit
def test_score_yield_curve_normal_is_low():
    """Normal steepening → growth regime → bearish gold → low score."""
    score = ind.score_yield_curve(us10y=4.5, us02y=3.0)   # +1.5 spread
    assert score < 35, f"Expected low score for normal curve, got {score}"


@pytest.mark.unit
def test_score_vix_crisis_is_high():
    """VIX spike → fear → safe-haven gold demand → high score."""
    assert ind.score_vix(35.0) > 75


@pytest.mark.unit
def test_score_vix_complacency_is_low():
    assert ind.score_vix(11.0) < 40


@pytest.mark.unit
def test_scores_are_bounded():
    """All component scores must stay in [0, 100]."""
    series = [100.0 + i * 0.1 for i in range(30)]
    for fn, args in [
        (ind.score_dxy,          (104.5, series)),
        (ind.score_yield_curve,  (4.35, 4.85)),
        (ind.score_real_rates,   (4.35, series)),
        (ind.score_vix,          (15.5,)),
        (ind.score_spx_momentum, (series,)),
        (ind.score_gold_momentum,(series,)),
    ]:
        score = fn(*args)
        assert 0 <= score <= 100, f"{fn.__name__} out of bounds: {score}"


@pytest.mark.unit
def test_compute_macro_score_range():
    components = {
        "dxy": 70, "yield_curve": 80, "real_rates": 60,
        "vix_fear": 75, "spx_momentum": 65, "gold_momentum": 70,
    }
    score = ind.compute_macro_score(components)
    assert 0 <= score <= 100


@pytest.mark.unit
def test_risk_score_high_vix():
    score = ind.compute_risk_score(vix=38.0, yield_spread=-1.5, spx_mom=-5.0)
    assert score > 70


@pytest.mark.unit
def test_risk_score_low_vix():
    score = ind.compute_risk_score(vix=12.0, yield_spread=1.0, spx_mom=3.0)
    assert score < 35


@pytest.mark.unit
def test_gold_bias_bullish_threshold():
    assert ind.classify_gold_bias(macro_score=70, risk_score=60) == "bullish"


@pytest.mark.unit
def test_gold_bias_bearish_threshold():
    assert ind.classify_gold_bias(macro_score=30, risk_score=25) == "bearish"


@pytest.mark.unit
def test_gold_bias_neutral_midrange():
    assert ind.classify_gold_bias(macro_score=50, risk_score=50) == "neutral"


@pytest.mark.unit
def test_classify_market_regime_risk_on():
    assert ind.classify_market_regime(vix=13.0, spx_mom=2.5, dxy_mom=0.1) == "risk_on"


@pytest.mark.unit
def test_classify_market_regime_risk_off():
    assert ind.classify_market_regime(vix=30.0, spx_mom=-5.0, dxy_mom=1.0) == "risk_off"


@pytest.mark.unit
def test_classify_liquidity():
    assert ind.classify_liquidity(us10y=2.0, vix=14.0, dxy=100.0) == "abundant"
    assert ind.classify_liquidity(us10y=5.5, vix=30.0, dxy=109.0) == "tight"
    assert ind.classify_liquidity(us10y=4.0, vix=20.0, dxy=103.0) == "normal"


@pytest.mark.unit
def test_confidence_high_when_aligned():
    components = {k: 80 for k in
                  ["dxy", "yield_curve", "real_rates", "vix_fear", "spx_momentum", "gold_momentum"]}
    conf = ind.compute_confidence(components, macro_score=80)
    assert conf > 70, f"Expected high confidence when all signals agree, got {conf}"


@pytest.mark.unit
def test_confidence_lower_when_mixed():
    components = {
        "dxy": 90, "yield_curve": 10, "real_rates": 85,
        "vix_fear": 15, "spx_momentum": 80, "gold_momentum": 20,
    }
    conf = ind.compute_confidence(components, macro_score=50)
    assert conf < 70, f"Expected lower confidence when signals conflict, got {conf}"


# ──────────────────────────────────────────────────────────────────
#  Engine integration tests
# ──────────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_returns_valid_analysis():
    engine = MacroTrendEngine(provider=MockMarketDataProvider(seed=42))
    result = await engine.analyze()

    assert 0 <= result.macro_score <= 100
    assert 0 <= result.risk_score  <= 100
    assert 0.0 <= result.confidence <= 100.0
    assert result.gold_bias in ("bullish", "neutral", "bearish")
    assert result.market_regime in ("risk_on", "risk_off", "transitional")
    assert result.macro_regime in (
        "hawkish_fed", "dovish_fed", "inflationary", "deflationary",
        "recession_risk", "growth_expansion", "neutral",
    )
    assert result.liquidity_conditions in ("abundant", "normal", "tight")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_snapshot_realistic_values():
    engine = MacroTrendEngine(provider=MockMarketDataProvider(seed=0))
    result = await engine.analyze()
    s = result.snapshot

    assert 1500 < s.xauusd < 3500,  f"Gold price unrealistic: {s.xauusd}"
    assert  90  < s.dxy    < 125,   f"DXY unrealistic: {s.dxy}"
    assert   0  < s.us10y  < 15,    f"US10Y unrealistic: {s.us10y}"
    assert   0  < s.vix    < 80,    f"VIX unrealistic: {s.vix}"
    assert 3000 < s.spx    < 8000,  f"SPX unrealistic: {s.spx}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_component_scores_bounded():
    engine = MacroTrendEngine(provider=MockMarketDataProvider(seed=7))
    result = await engine.analyze()
    c = result.components

    for field, value in c.model_dump().items():
        assert 0 <= value <= 100, f"Component {field} out of bounds: {value}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_scenarios_not_empty():
    engine = MacroTrendEngine(provider=MockMarketDataProvider(seed=3))
    result = await engine.analyze()
    assert result.primary_scenario
    assert result.alternate_scenario


# ──────────────────────────────────────────────────────────────────
#  HTTP endpoint tests
# ──────────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_macro_analysis_endpoint(client):
    response = client.get("/api/v1/macro/analysis")
    assert response.status_code == 200
    data = response.json()
    assert "macro_score" in data
    assert "risk_score" in data
    assert "gold_bias" in data
    assert "components" in data
    assert "snapshot" in data
    assert data["gold_bias"] in ("bullish", "neutral", "bearish")


@pytest.mark.unit
def test_macro_scores_endpoint(client):
    response = client.get("/api/v1/macro/scores")
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["macro_score"] <= 100
    assert 0 <= data["risk_score"]  <= 100
    assert data["gold_bias"] in ("bullish", "neutral", "bearish")


@pytest.mark.unit
def test_macro_regime_endpoint(client):
    response = client.get("/api/v1/macro/regime")
    assert response.status_code == 200
    data = response.json()
    assert "market_regime" in data
    assert "macro_regime" in data
    assert "liquidity_conditions" in data
    assert isinstance(data["key_signals"], list)
    assert isinstance(data["risk_factors"], list)


@pytest.mark.unit
def test_macro_snapshot_endpoint(client):
    response = client.get("/api/v1/macro/snapshot")
    assert response.status_code == 200
    data = response.json()
    for field in ["xauusd", "dxy", "us10y", "us02y", "spx", "vix", "yield_curve"]:
        assert field in data

    # yield_curve is 10Y-2Y: can be negative (inverted) — just check it's present and a number
    assert isinstance(data["yield_curve"], float)
    # These must be positive price/level values
    for field in ["xauusd", "dxy", "us10y", "us02y", "spx", "vix"]:
        assert data[field] > 0, f"{field} must be positive, got {data[field]}"
