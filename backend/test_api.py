import urllib.request
import json

endpoints = [
    ("Dashboard", "http://localhost:8000/api/dashboard"),
    ("Compliance Heatmap", "http://localhost:8000/api/compliance-heatmap"),
    ("Trend Analytics", "http://localhost:8000/api/trend-analytics"),
    ("Compliance Score", "http://localhost:8000/api/compliance-score/siltaraphase1"),
]

for name, url in endpoints:
    try:
        resp = urllib.request.urlopen(url, timeout=15)
        data = json.loads(resp.read())
        print(f"[OK] {name}: {list(data.keys())[:8]}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")

# Test encroachment new fields
try:
    req = urllib.request.Request(
        "http://localhost:8000/api/detect-encroachment",
        data=json.dumps({"region_id": "siltaraphase1"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    print(f"\n[OK] Encroachment Detection:")
    print(f"  total_plots: {data.get('total_plots')}")
    print(f"  encroachments_found: {data.get('encroachments_found')}")
    print(f"  total_affected_area_sqm: {data.get('total_affected_area_sqm')}")
    print(f"  compliance_score: {data.get('compliance_score')}")
    print(f"  compliance_category: {data.get('compliance_category')}")
    print(f"  avg_iou: {data.get('avg_iou')}")
    print(f"  avg_risk_score: {data.get('avg_risk_score')}")
    if data.get("encroachments"):
        e = data["encroachments"][0]
        print(f"  First encroachment IoU: {e.get('iou_score')}")
        print(f"  First encroachment risk: {e.get('risk_score')}")
        print(f"  First encroachment activity: {e.get('activity_status')}")
        print(f"  First encroachment deviation: {e.get('area_deviation_pct')}")
except Exception as e:
    print(f"[FAIL] Encroachment: {e}")

print("\nAll API tests complete.")
