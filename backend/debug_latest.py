import httpx

print("Testing latest endpoint...")
r = httpx.get('http://localhost:8000/api/v1/market/latest?symbol=XAUUSD')
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
