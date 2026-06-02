"""
Unit tests for Volatility Engine — Module 4.
"""

import math
import pytest
from datetime import UTC, datetime, timedelta

from app.schemas.market import OHLCVData
from app.services.volatility import calculator as calc
from app.services.volatility.engine import VolatilityEngine
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


def stable_candles(n: int = 60, price: float = 2050.0) -> list:
    """Low-volatility candles — constant price."""
    return [make_candle(price, i=i) for i in range(n)]


def volatile_candles(n: int = 60, price: float = 2050.0, vol: float = 0.02) -> list:
    """High-volatility candles — wide ranges."""
    candles = []
    p = price
    for i in range(n):
        p = p * (1 + (0.01 if i % 2 == 0 else -0.008))
        candles.append(make_candle(p, high=p * (1 + vol), low=p * (1 - vol), i=i))
    return candles


# ── True Range ────────────────────────────────────────────────────

@pytest.mark.unit
def test_true_range_basic():
    c = make_candle(2050.0, high=2060.0, low=2040.0)
    tr = calc.true_range(c, prev_close=2048.0)
    assert tr == pytest.approx(20.0)   # H-L is the widest


@pytest.mark.unit
def test_true_range_gap_up():
    c = make_candle(2100.0, high=2110.0, low=2095.0)
    tr = calc.true_range(c, prev_close=2050.0)
    assert tr == pytest.approx(60.0)   # H - prev_close is widest


@pytest.mark.unit
def test_true_range_always_positive():
    c = make_candle(2050.0, high=2055.0, low=2048.0)
    tr = calc.true_range(c, prev_close=2060.0)
    assert tr > 0


# ── ATR ───────────────────────────────────────────────────────────

@pytest.mark.unit
def test_atr_returns_series():
    candles = volatile_candles(40)
    atr_series = calc.compute_atr(candles, period=14)
    assert len(atr_series) > 0


@pytest.mark.unit
def test_atr_positive():
    candles = volatile_candles(40)
    for v in calc.compute_atr(candles, period=14):
        assert v >= 0


@pytest.mark.unit
def test_atr_stable_lower_than_volatile():
    atr_stable   = calc.compute_atr(stable_candles(40),   period=14)
    atr_volatile = calc.compute_atr(volatile_candles(40), period=14)
    assert atr_stable[-1] < atr_volatile[-1]


# ── Realized Volatility ───────────────────────────────────────────

@pytest.mark.unit
def test_realized_vol_positive():
    candles = volatile_candles(30)
    rv = calc.realized_vol(candles, 20)
    assert rv >= 0


@pytest.mark.unit
def test_realized_vol_stable_is_low():
    candles = stable_candles(60)
    rv = calc.realized_vol(candles, 20)
    assert rv < 1.0, f"Expected near-zero realized vol for stable candles, got {rv}"


@pytest.mark.unit
def test_realized_vol_volatile_is_high():
    candles = volatile_candles(60, vol=0.03)
    rv = calc.realized_vol(candles, 20)
    assert rv > 5.0, f"Expected high realized vol for volatile candles, got {rv}"


@pytest.mark.unit
def test_realized_vol_insufficient_data():
    candles = stable_candles(5)
    rv = calc.realized_vol(candles, window=20)
    assert rv == 0.0


# ── Range Analysis ────────────────────────────────────────────────

@pytest.mark.unit
def test_candle_range_pct():
    c = make_candle(2050.0, high=2070.0, low=2030.0)
    r = calc.candle_range_pct(c)
    assert r == pytest.approx(40.0 / 2050.0 * 100, rel=1e-3)


@pytest.mark.unit
def test_body_ratio_full_body():
    c = make_candle(2060.0, open_=2040.0, high=2062.0, low=2038.0)
    br = calc.body_ratio(c)
    assert 0 < br <= 1.0


@pytest.mark.unit
def test_body_ratio_doji():
    c = make_candle(2050.0, open_=2050.0, high=2060.0, low=2040.0)
    br = calc.body_ratio(c)
    assert br == pytest.approx(0.0, abs=0.001)


# ── Regime ────────────────────────────────────────────────────────

@pytest.mark.unit
def test_regime_compression():
    regime, vol, comp, exp = calc.classify_vol_regime(
        atr_pct=0.1, atr_zscore=-1.5, realized_20=2.0, range_compression=0.4
    )
    assert regime == "compression"
    assert comp > 50


@pytest.mark.unit
def test_regime_expansion():
    regime, vol, comp, exp = calc.classify_vol_regime(
        atr_pct=1.5, atr_zscore=2.0, realized_20=25.0, range_compression=1.8
    )
    assert regime in ("expansion", "high")
    assert exp > 50


@pytest.mark.unit
def test_regime_scores_bounded():
    for atr_pct, atr_z, rv, rc in [
        (0.1, -2.0, 1.0, 0.3),
        (0.5,  0.0, 8.0, 1.0),
        (1.5,  2.5, 30.0, 2.0),
    ]:
        r, v, c, e = calc.classify_vol_regime(atr_pct, atr_z, rv, rc)
        assert 0 <= v <= 100
        assert 0 <= c <= 100
        assert 0 <= e <= 100


@pytest.mark.unit
def test_vix_regime_labels():
    assert calc.classify_vix_regime(11.0) == "low"
    assert calc.classify_vix_regime(17.0) == "normal"
    assert calc.classify_vix_regime(25.0) == "elevated"
    assert calc.classify_vix_regime(35.0) == "spike"


@pytest.mark.unit
def test_market_vol_regime_calm():
    assert calc.classify_market_vol_regime(vix=12.0, gold_atr_pct=0.3) == "calm"


@pytest.mark.unit
def test_market_vol_regime_extreme():
    assert calc.classify_market_vol_regime(vix=32.0, gold_atr_pct=0.5) == "extreme"


# ── Engine integration ────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_analyze_valid():
    engine = VolatilityEngine(provider=MockMarketDataProvider(seed=42))
    r = await engine.analyze("XAUUSD", "1h")

    assert r.symbol == "XAUUSD"
    assert r.atr > 0
    assert r.atr_pct > 0
    assert r.regime in ("compression", "low", "medium", "high", "expansion", "unknown")
    assert 0 <= r.regime_score    <= 100
    assert 0 <= r.compression_score <= 100
    assert 0 <= r.expansion_score   <= 100
    assert r.realized_vol_20 >= 0
    assert r.candles_analyzed > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_summary_valid():
    engine = VolatilityEngine(provider=MockMarketDataProvider(seed=7))
    s = await engine.analyze_all()

    assert s.gold_regime in ("compression", "low", "medium", "high", "expansion", "unknown")
    assert s.vix_regime in ("low", "normal", "elevated", "spike")
    assert s.market_vol_regime in ("calm", "normal", "elevated", "extreme")
    assert s.vix_level > 0


# ── HTTP endpoints ────────────────────────────────────────────────

@pytest.mark.unit
def test_volatility_analysis_endpoint(client):
    r = client.get("/api/v1/volatility/analysis?symbol=XAUUSD&timeframe=1h")
    assert r.status_code == 200
    d = r.json()
    assert "regime" in d
    assert "atr_pct" in d
    assert "realized_vol_20" in d
    assert d["regime"] in ("compression", "low", "medium", "high", "expansion", "unknown")


@pytest.mark.unit
def test_volatility_regime_endpoint(client):
    r = client.get("/api/v1/volatility/regime?symbol=XAUUSD")
    assert r.status_code == 200
    d = r.json()
    assert 0 <= d["regime_score"]      <= 100
    assert 0 <= d["compression_score"] <= 100
    assert 0 <= d["expansion_score"]   <= 100


@pytest.mark.unit
def test_volatility_summary_endpoint(client):
    r = client.get("/api/v1/volatility/summary")
    assert r.status_code == 200
    d = r.json()
    assert "gold_regime" in d
    assert "vix_regime" in d
    assert "market_vol_regime" in d
    assert "readings" in d
