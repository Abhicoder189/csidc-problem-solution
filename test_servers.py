import requests
import json

print("Testing Backend API...")
print("-" * 50)

# Test 1: Health check
try:
    resp = requests.get("http://localhost:8000/health", timeout=5)
    print(f"✓ Health check: {resp.status_code}")
except Exception as e:
    print(f"✗ Health check failed: {e}")

# Test 2: Search all regions
try:
    resp = requests.get("http://localhost:8000/api/search-regions?q=", timeout=5)
    print(f"✓ Search all regions: {resp.status_code}")
    data = resp.json()
    print(f"  - Returned {len(data)} regions")
    if len(data) > 0:
        print(f"  - First region: {data[0]['name']} ({data[0]['region_id']})")
except Exception as e:
    print(f"✗ Search all failed: {e}")

# Test 3: Search for Siltara
try:
    resp = requests.get("http://localhost:8000/api/search-regions?q=siltara", timeout=5)
    print(f"✓ Search 'siltara': {resp.status_code}")
    data = resp.json()
    print(f"  - Found {len(data)} matches")
    for r in data:
        print(f"    • {r['name']} - {r['district']}")
except Exception as e:
    print(f"✗ Search 'siltara' failed: {e}")

print("-" * 50)
print("Testing Frontend...")
try:
    resp = requests.get("http://localhost:3000", timeout=5)
    print(f"✓ Frontend accessible: {resp.status_code}")
except Exception as e:
    print(f"✗ Frontend failed: {e}")
