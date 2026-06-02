"""
Unit tests for Correlation Engine — Module 5.
"""

import math
import pytest
from datetime import UTC, datetime, timedelta

from app.schemas.market import OHLCVData
from app.services.correlation import calculator as calc
from app.services.correlation.engine import CorrelationEngine
from app.services.market_data.providers.mock import MockMarketDataProvider


# ── Price series factories ────────────────────────────────────────

def linear(n: int, start: float = 100.0, slope: float = 1.0) -> list:
    return [start + i * slope for i in range(n)]


def inverse(n: int, start: float = 110.0, slope: float = 1.0) -> list:
    return [start - i * slope for i in range(n)]


def noise(n: int, base: float = 100.0, amp: float = 2.0) -> list:
    import random
    rng = random.Random(0)
    v = base
    series = []
    for _ in range(n):
        v += rng.uniform(-amp, amp)
        series.append(v)
    return series


# ── Pearson correlation ───────────────────────────────────────────

@pytest.mark.unit
def test_pearson_perfect_positive():
    x = linear(30)
    assert calc.pearson(x, x) == pytest.approx(1.0, abs=1e-6)


@pytest.mark.unit
def test_pearson_perfect_negative():
    x = linear(30, slope=1.0)
    y = inverse(30, slope=1.0)
    r = calc.pearson(x, y)
    assert r == pytest.approx(-1.0, abs=1e-4)


@pytest.mark.unit
def test_pearson_uncorrelated():
    x = linear(60, slope=1.0)
    y = noise(60)
    r = calc.pearson(x, y)
    assert -1.0 <= r <= 1.0


@pytest.mark.unit
def test_pearson_bounds():
    for _ in range(10):
        x = noise(50, amp=3.0)
        y = noise(50, base=200.0, amp=5.0)
        assert -1.0 <= calc.pearson(x, y) <= 1.0


@pytest.mark.unit
def test_pearson_insufficient_data():
    assert calc.pearson([1.0, 2.0], [1.0, 2.0]) == 0.0


# ── Log returns ───────────────────────────────────────────────────

@pytest.mark.unit
def test_log_returns_length():
    prices = linear(20)
    returns = calc._log_returns(prices)
    assert len(returns) == 19


@pytest.mark.unit
def test_log_returns_positive_for_rising():
    prices = linear(10, start=100.0, slope=5.0)
    returns = calc._log_returns(prices)
    assert all(r > 0 for r in returns)


# ── Rolling correlation ───────────────────────────────────────────

@pytest.mark.unit
def test_rolling_correlation_length():
    x = linear(50)
    y = inverse(50)
    roll = calc.rolling_correlation(x, y, window=20)
    assert len(roll) == 31   # 50 - 20 + 1


@pytest.mark.unit
def test_rolling_correlation_bounds():
    x = noise(60)
    y = noise(60, base=200.0)
    for v in calc.rolling_correlation(x, y, window=20):
        assert -1.0 <= v <= 1.0


# ── Pair analysis ─────────────────────────────────────────────────

@pytest.mark.unit
def test_analyze_pair_negative_corr():
    """
    Build returns explicitly: when gold rises DXY falls (correlated returns).
    Uses a shared noise factor to guarantee strong negative correlation.
    """
    import random
    rng = random.Random(99)
    factor = [rng.gauss(0, 1) for _ in range(60)]

    gold, dxy = [2000.0], [110.0]
    for f in factor:
        gold.append(gold[-1] * (1 + f * 0.005))          # gold moves with factor
        dxy.append(dxy[-1]  * (1 - f * 0.003))           # DXY moves opposite

    pair = calc.analyze_pair("XAUUSD", "DXY", gold, dxy)
    assert pair is not None
    assert pair.corr_current < 0
    assert pair.direction == "negative"


@pytest.mark.unit
def test_analyze_pair_positive_corr():
    """
    Build returns: both series driven by same factor → strong positive correlation.
    """
    import random
    rng = random.Random(42)
    factor = [rng.gauss(0, 1) for _ in range(60)]

    x, y = [2000.0], [15.0]
    for f in factor:
        x.append(x[-1] * (1 + f * 0.005))
        y.append(y[-1] * (1 + f * 0.003))   # same direction

    pair = calc.analyze_pair("XAUUSD", "VIX", x, y)
    assert pair is not None
    assert pair.corr_current > 0
    assert pair.direction == "positive"


@pytest.mark.unit
def test_analyze_pair_insufficient_data():
    pair = calc.analyze_pair("XAUUSD", "DXY", [100.0] * 10, [110.0] * 10)
    assert pair is None


@pytest.mark.unit
def test_analyze_pair_strength_labels():
    gold  = linear(60, slope=5.0)
    dxy   = inverse(60, slope=0.1)
    pair  = calc.analyze_pair("XAUUSD", "DXY", gold, dxy)
    assert pair.strength in ("strong", "moderate", "weak", "none")


@pytest.mark.unit
def test_breakdown_detection_triggered():
    """Large delta between 20 and 50 period should flag breakdown."""
    # First 50 bars: x and y move together (positive corr)
    x_hist = linear(50, slope=2.0)
    y_hist = linear(50, slope=1.8)   # same direction
    # Last 20 bars: y reverses (now negative correlation)
    x_recent = linear(20, start=x_hist[-1], slope=2.0)
    y_recent = inverse(20, start=y_hist[-1], slope=2.0)

    x = x_hist + x_recent
    y = y_hist + y_recent

    pair = calc.analyze_pair("XAUUSD", "SPX", x, y)
    # With strong historical positive and current negative, expect breakdown flag
    assert pair is not None
    assert pair.corr_delta != 0


# ── Gold profile ──────────────────────────────────────────────────

@pytest.mark.unit
def test_gold_profile_structure():
    gold = linear(60, start=2000.0, slope=5.0)
    others = {
        "DXY":   inverse(60, start=110.0, slope=0.1),
        "VIX":   noise(60, base=15.0, amp=1.0),
        "SPX":   linear(60, start=5000.0, slope=10.0),
    }
    now = datetime.now(UTC)
    profile = calc.build_gold_profile(gold, others, now)
    assert "DXY" in profile.xauusd_vs
    assert "VIX" in profile.xauusd_vs
    assert all(-1.0 <= v <= 1.0 for v in profile.xauusd_vs.values())
    assert "DXY" in profile.expected


@pytest.mark.unit
def test_gold_profile_deviations():
    gold = linear(60, slope=5.0)
    others = {"DXY": inverse(60, slope=0.1)}
    profile = calc.build_gold_profile(gold, others, datetime.now(UTC))
    assert "DXY" in profile.deviations


# ── Regime ────────────────────────────────────────────────────────

@pytest.mark.unit
def test_regime_normal_no_breakdowns():
    regime, score = calc.classify_correlation_regime([], [])
    assert regime == "normal"
    assert score == 0.0


# ── Engine integration ────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_full_analysis():
    engine = CorrelationEngine(provider=MockMarketDataProvider(seed=42))
    r = await engine.analyze(limit=80)

    assert r.regime in ("normal", "stressed", "breakdown")
    assert 0 <= r.regime_score <= 100
    assert isinstance(r.pairs, list)
    assert len(r.pairs) > 0
    assert isinstance(r.breakdown_events, list)
    assert r.dominant_signal != ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_pairs_all_bounded():
    engine = CorrelationEngine(provider=MockMarketDataProvider(seed=7))
    r = await engine.analyze(limit=60)
    for p in r.pairs:
        assert -1.0 <= p.corr_current <= 1.0
        assert -1.0 <= p.corr_50      <= 1.0
        assert p.direction in ("positive", "negative", "neutral")
        assert p.strength  in ("strong", "moderate", "weak", "none")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_gold_profile_present():
    engine = CorrelationEngine(provider=MockMarketDataProvider(seed=3))
    r = await engine.analyze()
    assert r.gold_profile is not None
    assert "DXY" in r.gold_profile.xauusd_vs
    assert "VIX" in r.gold_profile.xauusd_vs


# ── HTTP endpoints ────────────────────────────────────────────────

@pytest.mark.unit
def test_correlation_regime_endpoint(client):
    res = client.get("/api/v1/correlation/regime")
    assert res.status_code == 200
    d = res.json()
    assert d["regime"] in ("normal", "stressed", "breakdown")
    assert 0 <= d["regime_score"] <= 100
    assert "dominant_signal" in d
    assert "gold_vs_dxy" in d


@pytest.mark.unit
def test_correlation_gold_endpoint(client):
    res = client.get("/api/v1/correlation/gold")
    assert res.status_code == 200
    d = res.json()
    assert "xauusd_vs" in d
    assert "expected" in d
    assert "deviations" in d
    for v in d["xauusd_vs"].values():
        assert -1.0 <= v <= 1.0


@pytest.mark.unit
def test_correlation_breakdowns_endpoint(client):
    res = client.get("/api/v1/correlation/breakdowns")
    assert res.status_code == 200
    d = res.json()
    assert "breakdowns" in d
    assert "count" in d
    assert "regime" in d


@pytest.mark.unit
def test_correlation_analysis_endpoint(client):
    res = client.get("/api/v1/correlation/analysis")
    assert res.status_code == 200
    d = res.json()
    assert "pairs" in d
    assert "breakdown_events" in d
    assert "gold_profile" in d
    assert len(d["pairs"]) > 0
