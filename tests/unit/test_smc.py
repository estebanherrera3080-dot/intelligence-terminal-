"""
Unit tests for Smart Money Engine — Module 3.
All tests offline: mock provider, no DB, no network.
"""

import pytest
from datetime import UTC, datetime, timedelta

from app.schemas.market import OHLCVData
from app.services.smc import detector as det
from app.services.smc.engine import SmartMoneyEngine
from app.services.market_data.providers.mock import MockMarketDataProvider


# ── Candle factory ────────────────────────────────────────────────

def make_candle(close: float, open_: float = None, high: float = None,
                low: float = None, i: int = 0) -> OHLCVData:
    o = open_ if open_ is not None else close
    h = high  if high  is not None else max(o, close) * 1.001
    l = low   if low   is not None else min(o, close) * 0.999
    return OHLCVData(
        symbol="XAUUSD", timeframe="1h",
        open=o, high=h, low=l, close=close, volume=1_000_000,
        timestamp=datetime.now(UTC) - timedelta(hours=50 - i),
        data_source="test",
    )


def trending_up(n: int = 30) -> list:
    return [make_candle(2000 + i * 5, i=i) for i in range(n)]


def trending_down(n: int = 30) -> list:
    return [make_candle(2200 - i * 5, i=i) for i in range(n)]


# ── Swing detection ───────────────────────────────────────────────

@pytest.mark.unit
def test_find_swing_highs_basic():
    candles = [make_candle(c, i=i) for i, c in enumerate(
        [100, 102, 105, 102, 100, 98, 100, 103, 106, 103, 100]
    )]
    highs = det.find_swing_highs(candles, left=2, right=2)
    assert len(highs) > 0
    for idx in highs:
        assert candles[idx].high >= candles[idx - 1].high
        assert candles[idx].high >= candles[idx + 1].high


@pytest.mark.unit
def test_find_swing_lows_basic():
    candles = [make_candle(c, i=i) for i, c in enumerate(
        [106, 104, 101, 104, 106, 108, 105, 102, 105, 108]
    )]
    lows = det.find_swing_lows(candles, left=2, right=2)
    assert len(lows) > 0


# ── FVG ──────────────────────────────────────────────────────────

@pytest.mark.unit
def test_detect_bullish_fvg():
    """Three candles where candle[2].low > candle[0].high → bullish FVG."""
    c0 = make_candle(2000.0, high=2005.0, low=1995.0, i=0)
    c1 = make_candle(2010.0, high=2015.0, low=2006.0, i=1)   # impulse candle
    c2 = make_candle(2020.0, high=2025.0, low=2012.0, i=2)   # c2.low > c0.high

    zones = det.detect_fvg([c0, c1, c2], "XAUUSD", "1h", min_gap_pct=0.01)
    bullish = [z for z in zones if z.direction == "bullish"]
    assert len(bullish) >= 1
    assert bullish[0].bottom == c0.high
    assert bullish[0].top    == c2.low


@pytest.mark.unit
def test_detect_bearish_fvg():
    c0 = make_candle(2020.0, high=2025.0, low=2015.0, i=0)
    c1 = make_candle(2010.0, high=2014.0, low=2005.0, i=1)
    c2 = make_candle(2000.0, high=2009.0, low=1995.0, i=2)   # c2.high < c0.low

    zones = det.detect_fvg([c0, c1, c2], "XAUUSD", "1h", min_gap_pct=0.01)
    bearish = [z for z in zones if z.direction == "bearish"]
    assert len(bearish) >= 1


@pytest.mark.unit
def test_fvg_midpoint_correct():
    c0 = make_candle(2000.0, high=2004.0, low=1996.0, i=0)
    c1 = make_candle(2010.0, i=1)
    c2 = make_candle(2020.0, high=2024.0, low=2010.0, i=2)

    zones = det.detect_fvg([c0, c1, c2], "XAUUSD", "1h", min_gap_pct=0.01)
    bullish = [z for z in zones if z.direction == "bullish"]
    if bullish:
        z = bullish[0]
        assert abs(z.midpoint - (z.bottom + z.top) / 2) < 0.001


# ── Order Blocks ─────────────────────────────────────────────────

@pytest.mark.unit
def test_detect_bullish_order_block():
    """Bearish candle followed by strong bullish impulse → bullish OB."""
    candles = trending_up(10)
    # Insert a bearish candle then a strong bullish impulse
    candles.append(make_candle(2040.0, open_=2050.0, i=10))   # bearish
    candles.append(make_candle(2090.0, open_=2041.0, i=11))   # strong bull
    candles.append(make_candle(2095.0, i=12))

    blocks = det.detect_order_blocks(candles, "XAUUSD", "1h", min_move_pct=0.1)
    bullish = [b for b in blocks if b.direction == "bullish"]
    assert len(bullish) >= 1


@pytest.mark.unit
def test_detect_bearish_order_block():
    candles = trending_down(10)
    candles.append(make_candle(2150.0, open_=2140.0, i=10))   # bullish
    candles.append(make_candle(2100.0, open_=2149.0, i=11))   # strong bear
    candles.append(make_candle(2095.0, i=12))

    blocks = det.detect_order_blocks(candles, "XAUUSD", "1h", min_move_pct=0.1)
    bearish = [b for b in blocks if b.direction == "bearish"]
    assert len(bearish) >= 1


@pytest.mark.unit
def test_order_block_strength_bounded():
    candles = trending_up(15)
    blocks = det.detect_order_blocks(candles, "XAUUSD", "1h")
    for b in blocks:
        assert 0 <= b.strength <= 100


# ── Liquidity Sweeps ─────────────────────────────────────────────

@pytest.mark.unit
def test_liquidity_sweep_high():
    """
    Builds a clear swing high with candles on both sides (satisfies left=3, right=2),
    then a pullback, then a sweep candle that wicks above and closes below.
    """
    candles: list = []
    # Uptrend
    for i in range(15):
        candles.append(make_candle(2000 + i * 10, i=i))

    # Clear swing high at index 15 — highest candle, needs ≥2 lower candles after
    sh_high = 2200.0
    candles.append(OHLCVData(
        symbol="XAUUSD", timeframe="1h",
        open=2155.0, high=sh_high, low=2150.0, close=2155.0,
        volume=1_000_000,
        timestamp=datetime.now(UTC) - timedelta(hours=10),
        data_source="test",
    ))
    # 4 pullback candles below the swing high (satisfies right=2)
    for i in range(4):
        candles.append(make_candle(2180 - i * 15, i=16 + i))

    # Sweep candle: wick above sh_high, close clearly below it
    candles.append(OHLCVData(
        symbol="XAUUSD", timeframe="1h",
        open=2149.0, high=sh_high * 1.004,   # wick above swing high
        low=2140.0,  close=sh_high * 0.996,  # close below swing high
        volume=1_000_000,
        timestamp=datetime.now(UTC),
        data_source="test",
    ))

    _, events = det.detect_liquidity(candles, "XAUUSD", "1h")
    sweeps = [e for e in events if e.event_type == "LIQUIDITY_SWEEP_HIGH"]
    assert len(sweeps) >= 1
    assert sweeps[0].probability > 50


# ── Engine integration ────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_returns_valid_analysis():
    engine = SmartMoneyEngine(provider=MockMarketDataProvider(seed=42))
    r = await engine.analyze(symbol="XAUUSD", timeframe="1h", limit=50)

    assert r.symbol == "XAUUSD"
    assert r.timeframe == "1h"
    assert r.structure_bias in ("bullish", "neutral", "bearish")
    assert 0 <= r.bias_strength <= 100
    assert r.candles_analyzed > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_events_have_valid_types():
    engine = SmartMoneyEngine(provider=MockMarketDataProvider(seed=7))
    r = await engine.analyze(symbol="XAUUSD", timeframe="1h", limit=80)
    valid_types = {
        "BOS_BULLISH", "BOS_BEARISH", "CHOCH_BULLISH", "CHOCH_BEARISH",
        "FVG_BULLISH", "FVG_BEARISH", "ORDER_BLOCK_BULLISH", "ORDER_BLOCK_BEARISH",
        "EQUAL_HIGHS", "EQUAL_LOWS", "LIQUIDITY_SWEEP_HIGH", "LIQUIDITY_SWEEP_LOW",
    }
    for e in r.events:
        assert e.event_type in valid_types, f"Unknown event type: {e.event_type}"
        assert 0 <= e.intensity <= 100
        assert 0 <= e.probability <= 100


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_fvg_zones_valid():
    engine = SmartMoneyEngine(provider=MockMarketDataProvider(seed=3))
    r = await engine.analyze(symbol="XAUUSD", timeframe="1h", limit=80)
    for z in r.fvg_zones:
        assert z.top > z.bottom
        assert z.direction in ("bullish", "bearish")
        assert z.gap_size > 0


# ── HTTP endpoints ────────────────────────────────────────────────

@pytest.mark.unit
def test_smc_bias_endpoint(client):
    response = client.get("/api/v1/smc/bias?symbol=XAUUSD&timeframe=1h")
    assert response.status_code == 200
    data = response.json()
    assert data["structure_bias"] in ("bullish", "neutral", "bearish")
    assert 0 <= data["bias_strength"] <= 100
    assert "nearest_fvg_above" in data
    assert "nearest_ob_below" in data


@pytest.mark.unit
def test_smc_events_endpoint(client):
    response = client.get("/api/v1/smc/events?symbol=XAUUSD")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert isinstance(data["events"], list)


@pytest.mark.unit
def test_smc_zones_endpoint(client):
    response = client.get("/api/v1/smc/zones?symbol=XAUUSD")
    assert response.status_code == 200
    data = response.json()
    assert "fvg_zones" in data
    assert "order_blocks" in data
    assert "liquidity_levels" in data


@pytest.mark.unit
def test_smc_analysis_endpoint(client):
    response = client.get("/api/v1/smc/analysis?symbol=XAUUSD&timeframe=1h")
    assert response.status_code == 200
    data = response.json()
    assert "structure_bias" in data
    assert "events" in data
    assert "fvg_zones" in data
    assert "order_blocks" in data
