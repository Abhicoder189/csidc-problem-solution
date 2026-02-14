import requests

# Test search-regions endpoint
try:
    response = requests.get("http://localhost:8000/api/search-regions?q=siltara")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# Test empty search (should return all regions)
try:
    response = requests.get("http://localhost:8000/api/search-regions?q=")
    print(f"\nAll regions count: {len(response.json())}")
except Exception as e:
    print(f"Error: {e}")
