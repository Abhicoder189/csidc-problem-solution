import requests

print("Testing Analytics API Endpoints...")
print("=" * 60)

# Test region
region_id = "siltaraphase1"

# Test 1: GIS Analysis
try:
    url = f"http://localhost:8000/api/gis-analysis/{region_id}"
    print(f"\n1. Testing: {url}")
    resp = requests.get(url, timeout=10)
    print(f"   Status: {resp.status_code}")
    if resp.ok:
        data = resp.json()
        print(f"   ✓ Region: {data.get('region_id')}")
        print(f"   ✓ Plot analysis: {len(data.get('plot_analysis', []))} plots")
        print(f"   ✓ Avg IoU: {data.get('avg_iou')}")
    else:
        print(f"   ✗ Error: {resp.text}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

# Test 2: Region Summary
try:
    url = f"http://localhost:8000/api/region-summary/{region_id}"
    print(f"\n2. Testing: {url}")
    resp = requests.get(url, timeout=10)
    print(f"   Status: {resp.status_code}")
    if resp.ok:
        data = resp.json()
        print(f"   ✓ Region: {data.get('region_name')}")
        print(f"   ✓ Total plots: {data.get('total_plots')}")
        print(f"   ✓ Compliance grade: {data.get('compliance_grade')}")
    else:
        print(f"   ✗ Error: {resp.text}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

# Test 3: Compliance Score
try:
    url = f"http://localhost:8000/api/compliance-score/{region_id}"
    print(f"\n3. Testing: {url}")
    resp = requests.get(url, timeout=10)
    print(f"   Status: {resp.status_code}")
    if resp.ok:
        data = resp.json()
        print(f"   ✓ Region: {data.get('region_name')}")
        print(f"   ✓ Compliance score: {data.get('compliance_score')}")
        print(f"   ✓ Risk level: {data.get('risk_level')}")
    else:
        print(f"   ✗ Error: {resp.text}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

# Test 4: Satellite Image (current)
try:
    url = "http://localhost:8000/api/satellite-image?lat=21.32&lon=81.69&bbox_km=2"
    print(f"\n4. Testing: {url}")
    resp = requests.get(url, timeout=10)
    print(f"   Status: {resp.status_code}")
    if resp.ok:
        data = resp.json()
        print(f"   ✓ Image URL: {data.get('image_url')[:80]}...")
        print(f"   ✓ Date: {data.get('date')}")
    else:
        print(f"   ✗ Error: {resp.text}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

# Test 5: Satellite Image (historical)
try:
    url = "http://localhost:8000/api/satellite-image?lat=21.32&lon=81.69&bbox_km=2&date=2020-01-15"
    print(f"\n5. Testing: {url}")
    resp = requests.get(url, timeout=10)
    print(f"   Status: {resp.status_code}")
    if resp.ok:
        data = resp.json()
        print(f"   ✓ Image URL: {data.get('image_url')[:80]}...")
        print(f"   ✓ Date: {data.get('date')}")
    else:
        print(f"   ✗ Error: {resp.text}")
except Exception as e:
    print(f"   ✗ Exception: {e}")

print("\n" + "=" * 60)
