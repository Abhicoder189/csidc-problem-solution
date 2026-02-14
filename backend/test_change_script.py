
import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO)

from services.change_detection import detect_changes

async def test():
    # Test a few different parameters
    tasks = [
        # Siltara (Phase 1)
        detect_changes(21.322, 81.688, "2020-01-15", "2026-02-14", bbox_km=2.0),
        # Urla (Plot 1)
        detect_changes(21.252, 81.579, "2020-01-15", "2026-02-14", bbox_km=2.0),
        # A known area with change (Borai)
        detect_changes(21.212, 81.349, "2020-01-15", "2026-02-14", bbox_km=2.0),
    ]

    results = await asyncio.gather(*tasks)
    
    for i, r in enumerate(results):
        print(f"\n--- Result {i} ---")
        if "error" in r:
            print("ERROR:", r["error"])
        else:
            print("Changed area:", r.get("changed_area_pct"), "%")
            print("NDVI change:", r.get("ndvi_change"))
            print("Processing time:", r.get("processing_time_ms"), "ms")
            print("Release dates:", r.get("release_before"), "->", r.get("release_after"))
            print("Features detected:", len(r.get("change_geojson", {}).get("features", [])))

if __name__ == "__main__":
    asyncio.run(test())
