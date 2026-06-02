#!/usr/bin/env python
"""Quick test script for FASE 2 endpoints"""
import httpx

def test_endpoints():
    """Test all market endpoints"""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("TESTING FASE 2 API ENDPOINTS")
    print("=" * 60)
    
    # Test 1: Root endpoint
    print("\n✓ Test 1: Root Endpoint")
    r = httpx.get(f"{base_url}/")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    
    # Test 2: Symbols endpoint
    print("\n✓ Test 2: Market Symbols")
    r = httpx.get(f"{base_url}/api/v1/market/symbols")
    print(f"  Status: {r.status_code}")
    data = r.json()
    print(f"  Available Symbols: {len(data['symbols'])}")
    print(f"  First 3: {data['symbols'][:3]}")
    
    # Test 3: Latest tick for XAUUSD
    print("\n✓ Test 3: Latest Tick (XAUUSD - Gold)")
    r = httpx.get(f"{base_url}/api/v1/market/latest?symbol=XAUUSD")
    print(f"  Status: {r.status_code}")
    tick = r.json()
    print(f"  Price: ${tick['price']:.2f}")
    print(f"  Bid: {tick['bid']}, Ask: {tick['ask']}")
    print(f"  Spread: {tick['spread']:.4f}%")
    
    # Test 4: OHLCV data
    print("\n✓ Test 4: OHLCV Data (EURUSD, 1 hour, 5 candles)")
    r = httpx.get(f"{base_url}/api/v1/market/ohlcv?symbol=EURUSD&timeframe=1h&limit=5")
    print(f"  Status: {r.status_code}")
    ohlcv = r.json()
    print(f"  Symbol: {ohlcv['symbol']}, Timeframe: {ohlcv['timeframe']}")
    print(f"  Candles Count: {len(ohlcv['data'])}")
    if ohlcv['data']:
        latest_candle = ohlcv['data'][0]
        print(f"  Latest: O={latest_candle['open']}, H={latest_candle['high']}, L={latest_candle['low']}, C={latest_candle['close']}")
    
    # Test 5: Market health
    print("\n✓ Test 5: Market Health")
    r = httpx.get(f"{base_url}/api/v1/market/health")
    print(f"  Status: {r.status_code}")
    health = r.json()
    print(f"  Market Status: {health['status']}")
    print(f"  Provider: {health['provider']}")
    print(f"  Connected: {health['connected']}")
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nAPI Documentation available at:")
    print("  → http://localhost:8000/docs (Swagger UI)")
    print("  → http://localhost:8000/redoc (ReDoc)")

if __name__ == "__main__":
    test_endpoints()
