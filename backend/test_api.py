"""
Quick test script for FASE 2 API endpoints
"""

import asyncio
import sys

from app.services.market_data.providers.twelve_data import TwelveDataProvider


async def test_market_data_api():
    """Test market data provider"""
    print("=" * 60)
    print("🚀 INTELLIGENCE TERMINAL - MARKET DATA API TEST")
    print("=" * 60)

    provider = TwelveDataProvider(api_key="demo")

    # Test 1: Get available symbols
    print("\n1️⃣  Testing: Get Available Symbols")
    print("-" * 60)
    try:
        symbols = await provider.get_available_symbols()
        print(f"✅ Symbols fetched: {len(symbols)}")
        print(f"   Examples: {', '.join(symbols[:5])}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Fetch OHLCV data
    print("\n2️⃣  Testing: Fetch OHLCV Data (XAUUSD)")
    print("-" * 60)
    try:
        ohlcv = await provider.fetch_ohlcv("XAUUSD", timeframe="1h", limit=5)
        if ohlcv:
            print(f"✅ Candles fetched: {len(ohlcv)}")
            for i, candle in enumerate(ohlcv[-3:], 1):
                print(f"   [{i}] {candle.timestamp} | O:{candle.open:.2f} H:{candle.high:.2f} L:{candle.low:.2f} C:{candle.close:.2f}")
        else:
            print("⚠️  No data returned")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: Fetch latest tick
    print("\n3️⃣  Testing: Fetch Latest Tick (XAUUSD)")
    print("-" * 60)
    try:
        tick = await provider.fetch_latest_tick("XAUUSD")
        print(f"✅ Tick fetched:")
        print(f"   Price: ${tick.price:.2f}")
        print(f"   Bid: ${tick.bid:.2f}")
        print(f"   Ask: ${tick.ask:.2f}")
        print(f"   Spread: ${(tick.ask - tick.bid):.4f}")
        print(f"   Volume: {tick.volume:.0f}")
        print(f"   Time: {tick.timestamp}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 4: Multiple symbols
    print("\n4️⃣  Testing: Multiple Symbols (Latest Prices)")
    print("-" * 60)
    test_symbols = ["XAUUSD", "EURUSD", "GBPUSD", "DXY"]
    for sym in test_symbols:
        try:
            tick = await provider.fetch_latest_tick(sym)
            print(f"✅ {sym}: ${tick.price:.4f}")
        except Exception as e:
            print(f"❌ {sym}: {e}")

    # Test 5: Connection validation
    print("\n5️⃣  Testing: Connection Validation")
    print("-" * 60)
    try:
        connected = await provider.validate_connection()
        status = "✅ CONNECTED" if connected else "❌ DISCONNECTED"
        print(f"{status}")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_market_data_api())
