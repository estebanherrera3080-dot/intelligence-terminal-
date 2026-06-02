"""
Unit tests for market data routes and mock provider.
DB is replaced with a no-op mock (see conftest.py) — no PostgreSQL required.
"""

import pytest

from app.services.market_data.providers.mock import MockMarketDataProvider
from app.services.market_data.service import TRACKED_SYMBOLS


# ------------------------------------------------------------------ #
#  MockMarketDataProvider — unit tests                                #
# ------------------------------------------------------------------ #

@pytest.mark.unit
def test_mock_provider_tracked_symbols_present():
    provider = MockMarketDataProvider()
    for sym in TRACKED_SYMBOLS:
        assert sym in provider.SYMBOLS, f"{sym} missing from mock provider"


@pytest.mark.unit
def test_mock_provider_realistic_prices():
    """Verify base prices are in plausible institutional ranges."""
    p = MockMarketDataProvider.BASE_PRICES
    assert 1500 < p["XAUUSD"] < 3500,  "Gold price out of range"
    assert 90   < p["DXY"]   < 120,    "DXY out of range"
    assert 1    < p["US10Y"] < 10,     "US10Y yield out of range"
    assert 1    < p["US02Y"] < 10,     "US02Y yield out of range"
    assert 3000 < p["SPX"]   < 8000,   "SPX out of range"
    assert 5    < p["VIX"]   < 50,     "VIX out of range"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_provider_ohlcv_count():
    provider = MockMarketDataProvider(seed=42)
    data = await provider.fetch_ohlcv(symbol="XAUUSD", timeframe="1h", limit=10)
    assert len(data) == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_provider_ohlcv_reproducible():
    p1 = MockMarketDataProvider(seed=42)
    p2 = MockMarketDataProvider(seed=42)
    d1 = await p1.fetch_ohlcv("XAUUSD", limit=5)
    d2 = await p2.fetch_ohlcv("XAUUSD", limit=5)
    assert [c.close for c in d1] == [c.close for c in d2]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_provider_ohlcv_candlestick_integrity():
    provider = MockMarketDataProvider(seed=0)
    data = await provider.fetch_ohlcv("XAUUSD", limit=50)
    for c in data:
        assert c.high >= c.open,  "high < open"
        assert c.high >= c.close, "high < close"
        assert c.low  <= c.open,  "low > open"
        assert c.low  <= c.close, "low > close"
        assert c.volume >= 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_provider_tick_bid_lt_ask():
    provider = MockMarketDataProvider(seed=42)
    tick = await provider.fetch_latest_tick("XAUUSD")
    assert tick.bid < tick.ask
    assert tick.bid > 0
    assert tick.price == round((tick.bid + tick.ask) / 2, 5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_provider_all_tracked_symbols_ohlcv():
    """All 7 institutional symbols must return data (not fallback 100.0)."""
    provider = MockMarketDataProvider(seed=1)
    for sym in TRACKED_SYMBOLS:
        data = await provider.fetch_ohlcv(sym, limit=3)
        assert len(data) == 3, f"No data for {sym}"
        # price should be in a realistic range (not the 100.0 fallback)
        assert data[0].close != 100.0, f"{sym} using fallback price"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_provider_validate_connection():
    assert await MockMarketDataProvider().validate_connection() is True


# ------------------------------------------------------------------ #
#  HTTP route tests (PostgreSQL replaced with mock — see conftest)    #
# ------------------------------------------------------------------ #

@pytest.mark.unit
def test_market_symbols_endpoint(client):
    response = client.get("/api/v1/market/symbols")
    assert response.status_code == 200
    data = response.json()
    assert "symbols" in data
    assert "XAUUSD" in data["symbols"]
    assert data["count"] == len(data["symbols"])


@pytest.mark.unit
def test_market_latest_endpoint(client):
    response = client.get("/api/v1/market/latest?symbol=XAUUSD")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "XAUUSD"
    assert data["bid"] < data["ask"]
    assert data["spread"] > 0
    assert "timestamp" in data


@pytest.mark.unit
def test_market_latest_all_endpoint(client):
    response = client.get("/api/v1/market/latest/all")
    assert response.status_code == 200
    data = response.json()
    for sym in TRACKED_SYMBOLS:
        assert sym in data, f"{sym} missing from /latest/all"
        assert data[sym]["price"] > 0
        assert "timestamp" in data[sym]


@pytest.mark.unit
def test_market_ohlcv_endpoint(client):
    response = client.get("/api/v1/market/ohlcv?symbol=XAUUSD&timeframe=1h&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "XAUUSD"
    assert data["count"] == 5
    assert len(data["data"]) == 5


@pytest.mark.unit
def test_market_ohlcv_limit_too_large(client):
    response = client.get("/api/v1/market/ohlcv?symbol=XAUUSD&limit=99999")
    assert response.status_code == 422


@pytest.mark.unit
def test_market_health_endpoint(client):
    response = client.get("/api/v1/market/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "XAUUSD" in data["tracked_symbols"]
