import requests

print("Testing Satellite Image API...")
print("=" * 70)

# Test current image
lat, lon = 21.32, 81.69
url = f"http://localhost:8000/api/satellite-image?lat={lat}&lon={lon}&bbox_km=2"
print(f"\nTest 1: Current Image")
print(f"URL: {url}")

try:
    resp = requests.get(url, timeout=10)
    if resp.ok:
        data = resp.json()
        print(f"✓ Status: {resp.status_code}")
        print(f"✓ Image URL: {data['image_url']}")
        print(f"✓ Date: {data['date']}")
        print(f"\nTesting if image URL is accessible...")
        
        # Try to fetch the actual image
        img_resp = requests.get(data['image_url'], timeout=15)
        print(f"✓ Image HTTP Status: {img_resp.status_code}")
        print(f"✓ Content-Type: {img_resp.headers.get('Content-Type')}")
        print(f"✓ Content-Length: {len(img_resp.content)} bytes")
        
        if img_resp.ok and 'image' in img_resp.headers.get('Content-Type', ''):
            print("✅ Current image is accessible!")
        else:
            print("❌ Image URL returned unexpected content")
    else:
        print(f"❌ API Error: {resp.status_code}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test historical image
url = f"http://localhost:8000/api/satellite-image?lat={lat}&lon={lon}&bbox_km=2&date=2020-01-15"
print(f"\n" + "=" * 70)
print(f"Test 2: Historical Image (2020-01-15)")
print(f"URL: {url}")

try:
    resp = requests.get(url, timeout=10)
    if resp.ok:
        data = resp.json()
        print(f"✓ Status: {resp.status_code}")
        print(f"✓ Image URL: {data['image_url']}")
        print(f"✓ Date: {data['date']}")
        print(f"\nTesting if image URL is accessible...")
        
        # Try to fetch the actual image
        img_resp = requests.get(data['image_url'], timeout=15)
        print(f"✓ Image HTTP Status: {img_resp.status_code}")
        print(f"✓ Content-Type: {img_resp.headers.get('Content-Type')}")
        print(f"✓ Content-Length: {len(img_resp.content)} bytes")
        
        if img_resp.ok and 'image' in img_resp.headers.get('Content-Type', ''):
            print("✅ Historical image is accessible!")
        else:
            print("❌ Image URL returned unexpected content")
    else:
        print(f"❌ API Error: {resp.status_code}")
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "=" * 70)
print("\n💡 TIP: Open test_esri_images.html in a browser to test image display")
