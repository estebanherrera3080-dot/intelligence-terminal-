import httpx

print("Testing symbols endpoint...")
r = httpx.get('http://localhost:8000/api/v1/market/symbols')
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
