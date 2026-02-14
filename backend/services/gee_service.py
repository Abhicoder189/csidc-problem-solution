"""
ILMCS — Google Earth Engine Service
Handles Sentinel-2 imagery fetching, NDVI computation, and tile serving.
"""

import os
import uuid
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ── Chhattisgarh Industrial Region Catalog — ALL 56 REGIONS ────────
# Category: "new" = 36 new industrial areas, "old" = 20 established areas

REGION_CATALOG = {
    # ─── NEW INDUSTRIAL AREAS (36) ────────────────────────────────
    "khaprikhurd":              {"lat": 21.1600, "lon": 81.7100, "district": "Raipur",        "category": "new"},
    "narayanbahali":            {"lat": 21.3000, "lon": 81.5500, "district": "Raipur",        "category": "new"},
    "aurethibhatapara":         {"lat": 21.7300, "lon": 81.9500, "district": "Balodabazar",   "category": "new"},
    "siyarpalimahuapali":       {"lat": 21.4200, "lon": 81.6800, "district": "Raipur",        "category": "new"},
    "rikhi":                    {"lat": 21.3500, "lon": 81.6000, "district": "Raipur",        "category": "new"},
    "metalparkphase2a":         {"lat": 21.3300, "lon": 81.7200, "district": "Raipur",        "category": "new"},
    "metalparkphase2b":         {"lat": 21.3400, "lon": 81.7300, "district": "Raipur",        "category": "new"},
    "foodparksector1":          {"lat": 21.3100, "lon": 81.6500, "district": "Raipur",        "category": "new"},
    "foodparksector2":          {"lat": 21.3000, "lon": 81.6600, "district": "Raipur",        "category": "new"},
    "pangrikhurd":              {"lat": 21.2800, "lon": 81.5700, "district": "Raipur",        "category": "new"},
    "barbaspur":                {"lat": 21.3800, "lon": 81.5900, "district": "Raipur",        "category": "new"},
    "gangapurkhurdambikapur":   {"lat": 23.1000, "lon": 83.1800, "district": "Surguja",       "category": "new"},
    "textilepark":              {"lat": 21.3200, "lon": 81.6300, "district": "Raipur",        "category": "new"},
    "tilda":                    {"lat": 21.4600, "lon": 81.6200, "district": "Raipur",        "category": "new"},
    "abhanpur":                 {"lat": 21.0900, "lon": 81.7400, "district": "Raipur",        "category": "new"},
    "teknar":                   {"lat": 21.2300, "lon": 81.3200, "district": "Durg",          "category": "new"},
    "lakhanpuri":               {"lat": 21.2700, "lon": 81.4800, "district": "Durg",          "category": "new"},
    "hathkerabidbida":          {"lat": 21.4000, "lon": 81.7000, "district": "Raipur",        "category": "new"},
    "kesda":                    {"lat": 21.2000, "lon": 81.6500, "district": "Raipur",        "category": "new"},
    "engineeringpark":          {"lat": 21.3100, "lon": 81.6800, "district": "Raipur",        "category": "new"},
    "silpahari":                {"lat": 21.9000, "lon": 83.3800, "district": "Raigarh",       "category": "new"},
    "parasgarhi":               {"lat": 21.1500, "lon": 82.0800, "district": "Mahasamund",    "category": "new"},
    "mahroomkhurd":             {"lat": 21.2500, "lon": 81.5400, "district": "Raipur",        "category": "new"},
    "railpark":                 {"lat": 21.4700, "lon": 81.6100, "district": "Raipur",        "category": "new"},
    "khamaria":                 {"lat": 21.3700, "lon": 81.5800, "district": "Raipur",        "category": "new"},
    "readymadegarmentsparknr":  {"lat": 21.1800, "lon": 81.7900, "district": "Raipur",        "category": "new"},
    "pharmaceuticalparknr":     {"lat": 21.1700, "lon": 81.7800, "district": "Raipur",        "category": "new"},
    "gjamgoan":                 {"lat": 21.2200, "lon": 81.4000, "district": "Durg",          "category": "new"},
    "farsabahar":               {"lat": 23.1800, "lon": 83.8200, "district": "Jashpur",       "category": "new"},
    "plasticpark":              {"lat": 21.3300, "lon": 81.6700, "district": "Raipur",        "category": "new"},
    "selar":                    {"lat": 21.2900, "lon": 81.5300, "district": "Raipur",        "category": "new"},
    "shyamtarai":               {"lat": 21.4500, "lon": 81.6000, "district": "Raipur",        "category": "new"},
    "foodparksukma":            {"lat": 18.8700, "lon": 81.6600, "district": "Sukma",         "category": "new"},
    "ulakiya":                  {"lat": 21.4300, "lon": 81.6300, "district": "Raipur",        "category": "new"},
    "chandanuraveli":           {"lat": 21.1000, "lon": 81.0800, "district": "Rajnandgaon",   "category": "new"},
    "parasiya":                 {"lat": 21.0500, "lon": 80.9500, "district": "Rajnandgaon",   "category": "new"},

    # ─── OLD / ESTABLISHED INDUSTRIAL AREAS (20) ──────────────────
    "amaseoni":                 {"lat": 21.2200, "lon": 81.7000, "district": "Raipur",        "category": "old"},
    "bhanpuri":                 {"lat": 21.2700, "lon": 81.6100, "district": "Raipur",        "category": "old"},
    "birkoni":                  {"lat": 21.2000, "lon": 81.6800, "district": "Raipur",        "category": "old"},
    "borai":                    {"lat": 21.2100, "lon": 81.3500, "district": "Durg",          "category": "old"},
    "electronicemc":            {"lat": 21.2600, "lon": 81.6200, "district": "Raipur",        "category": "old"},
    "gogoan":                   {"lat": 21.1900, "lon": 81.6200, "district": "Raipur",        "category": "old"},
    "gondwara":                 {"lat": 21.2300, "lon": 81.6000, "district": "Raipur",        "category": "old"},
    "harinchhapara":            {"lat": 21.2100, "lon": 81.6400, "district": "Raipur",        "category": "old"},
    "kapan":                    {"lat": 21.2400, "lon": 81.6300, "district": "Raipur",        "category": "old"},
    "nayanpurgibarganj":        {"lat": 21.2600, "lon": 81.6500, "district": "Raipur",        "category": "old"},
    "ranidurgawatianjani":      {"lat": 23.5800, "lon": 83.0500, "district": "Korea",         "category": "old"},
    "rawabhata":                {"lat": 21.2300, "lon": 81.6900, "district": "Raipur",        "category": "old"},
    "siltaraphase1":            {"lat": 21.3200, "lon": 81.6900, "district": "Raipur",        "category": "old"},
    "siltaraphase2":            {"lat": 21.3300, "lon": 81.7000, "district": "Raipur",        "category": "old"},
    "sirgitti":                 {"lat": 22.1000, "lon": 82.1500, "district": "Bilaspur",      "category": "old"},
    "sondongari":               {"lat": 21.9100, "lon": 83.3900, "district": "Raigarh",       "category": "old"},
    "tenduaphase1":             {"lat": 21.3000, "lon": 81.5900, "district": "Raipur",        "category": "old"},
    "tenduaphase2":             {"lat": 21.3100, "lon": 81.5800, "district": "Raipur",        "category": "old"},
    "tifra":                    {"lat": 22.0800, "lon": 82.1400, "district": "Bilaspur",      "category": "old"},
    "urla":                     {"lat": 21.2500, "lon": 81.5800, "district": "Raipur",        "category": "old"},
}

# Friendly display name mapping
REGION_DISPLAY_NAMES = {
    "khaprikhurd": "Khapri Khurd", "narayanbahali": "Narayanbahali",
    "aurethibhatapara": "Aurethi Bhatapara", "siyarpalimahuapali": "Siyarpali-Mahuapali",
    "rikhi": "Rikhi", "metalparkphase2a": "Metal Park Phase II Sector A",
    "metalparkphase2b": "Metal Park Phase II Sector B", "foodparksector1": "Food Park Sector 1",
    "foodparksector2": "Food Park Sector 2", "pangrikhurd": "Pangrikhurd",
    "barbaspur": "Barbaspur", "gangapurkhurdambikapur": "Gangapur Khurd Ambikapur",
    "textilepark": "Textile Park", "tilda": "Tilda",
    "abhanpur": "Industrial Area Abhanpur", "teknar": "Teknar",
    "lakhanpuri": "Lakhanpuri", "hathkerabidbida": "Hathkera-Bidbida",
    "kesda": "Kesda", "engineeringpark": "Engineering Park",
    "silpahari": "Silpahari", "parasgarhi": "Parasgarhi",
    "mahroomkhurd": "Mahroomkhurd", "railpark": "Rail Park",
    "khamaria": "Khamaria", "readymadegarmentsparknr": "Readymade Garments Park Nava Raipur",
    "pharmaceuticalparknr": "Pharmaceutical Park Nava Raipur", "gjamgoan": "G-Jamgoan",
    "farsabahar": "Farsabahar", "plasticpark": "Plastic Park",
    "selar": "Selar", "shyamtarai": "Shyamtarai",
    "foodparksukma": "Food Park Sukma", "ulakiya": "Ulakiya",
    "chandanuraveli": "Chandanu Raveli", "parasiya": "Parasiya",
    "amaseoni": "Amaseoni", "bhanpuri": "Bhanpuri", "birkoni": "Birkoni",
    "borai": "Borai", "electronicemc": "Electronic EMC", "gogoan": "Gogoan",
    "gondwara": "Gondwara", "harinchhapara": "Harinchhapara", "kapan": "Kapan",
    "nayanpurgibarganj": "Nayanpur-Gibarganj", "ranidurgawatianjani": "Ranidurgawati Anjani",
    "rawabhata": "Rawabhata", "siltaraphase1": "Siltara Phase 1",
    "siltaraphase2": "Siltara Phase 2", "sirgitti": "Sirgitti",
    "sondongari": "Sondongari", "tenduaphase1": "Tendua Phase 1",
    "tenduaphase2": "Tendua Phase 2", "tifra": "Tifra", "urla": "Urla",
}


def _km_to_deg(km: float, lat: float) -> Tuple[float, float]:
    """Convert km to approximate degrees at given latitude."""
    lat_deg = km / 111.32
    lon_deg = km / (111.32 * math.cos(math.radians(lat)))
    return lat_deg, lon_deg


def resolve_region(name: Optional[str], lat: Optional[float], lon: Optional[float]) -> Dict:
    """Resolve region name or coordinates to center point."""
    if name:
        key = name.lower().strip().replace(" ", "").replace("-", "").replace("_", "")
        if key in REGION_CATALOG:
            info = REGION_CATALOG[key]
            display = REGION_DISPLAY_NAMES.get(key, name.title())
            return {"lat": info["lat"], "lon": info["lon"], "name": display,
                    "district": info["district"], "category": info["category"]}
        # Fuzzy match — check substrings both ways
        for k, v in REGION_CATALOG.items():
            if key in k or k in key:
                display = REGION_DISPLAY_NAMES.get(k, k.title())
                return {"lat": v["lat"], "lon": v["lon"], "name": display,
                        "district": v["district"], "category": v["category"]}

    if lat is not None and lon is not None:
        return {"lat": lat, "lon": lon, "name": f"Custom ({lat:.4f}, {lon:.4f})",
                "district": "Custom", "category": "custom"}

    raise ValueError("Provide either region_name or latitude/longitude coordinates.")


def build_bbox(lat: float, lon: float, bbox_km: float) -> Dict[str, float]:
    """Build bounding box dict from center point and half-width."""
    dlat, dlon = _km_to_deg(bbox_km, lat)
    return {
        "min_lat": round(lat - dlat, 6),
        "max_lat": round(lat + dlat, 6),
        "min_lon": round(lon - dlon, 6),
        "max_lon": round(lon + dlon, 6),
    }


def fetch_sentinel2_imagery(
    lat: float,
    lon: float,
    bbox_km: float = 5.0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    cloud_cover_max: int = 20,
) -> Dict:
    """
    Fetch Sentinel-2 imagery via Google Earth Engine.
    
    In production, this calls the GEE Python API. In demo mode,
    we return Mapbox-based tile URLs that show real satellite imagery.
    """
    bbox = build_bbox(lat, lon, bbox_km)
    
    if not start_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    try:
        import ee
        # Production GEE path
        ee.Initialize()
        
        aoi = ee.Geometry.Rectangle([bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"]])
        
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover_max))
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )
        
        count = collection.size().getInfo()
        if count == 0:
            raise ValueError(f"No Sentinel-2 images found for the given parameters.")
        
        image = collection.first()
        info = image.getInfo()
        acq_date = info["properties"].get("GENERATION_TIME", start_date)
        cloud = info["properties"].get("CLOUDY_PIXEL_PERCENTAGE", 0)
        
        # Generate visualization URLs
        vis_params = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.3}
        rgb_url = image.getThumbURL({**vis_params, "region": aoi, "dimensions": "1024x1024"})
        
        # NDVI
        ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        ndvi_url = ndvi.getThumbURL({
            "min": -0.2, "max": 0.8,
            "palette": ["red", "yellow", "green"],
            "region": aoi, "dimensions": "1024x1024",
        })
        
        return {
            "image_url": rgb_url,
            "thumbnail_url": rgb_url,
            "ndvi_url": ndvi_url,
            "acquisition_date": acq_date,
            "cloud_cover": cloud,
            "bands": ["B2", "B3", "B4", "B8"],
            "metadata": {"source": "GEE", "collection": "COPERNICUS/S2_SR_HARMONIZED", "count": count},
        }
    except ImportError:
        logger.info("GEE not available — using Mapbox satellite tiles (demo mode)")
    except Exception as e:
        logger.warning(f"GEE fetch failed: {e} — falling back to Mapbox tiles")

    # ── Fallback: use Mapbox/ESRI satellite tiles ──────────────────
    z = 14
    tile_url = (
        f"https://server.arcgisonline.com/ArcGIS/rest/services/"
        f"World_Imagery/MapServer/tile/{z}/{{y}}/{{x}}"
    )
    
    return {
        "image_url": f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
                     f"?bbox={bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}"
                     f"&bboxSR=4326&imageSR=4326&size=1024,1024&format=png&f=image",
        "thumbnail_url": f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
                         f"?bbox={bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}"
                         f"&bboxSR=4326&imageSR=4326&size=512,512&format=png&f=image",
        "ndvi_url": None,
        "acquisition_date": end_date,
        "cloud_cover": 0,
        "bands": ["R", "G", "B"],
        "metadata": {"source": "ESRI_WorldImagery", "mode": "demo"},
    }


def compute_ndvi_stats(lat: float, lon: float, bbox_km: float, date_str: str) -> Dict:
    """Compute NDVI statistics for an area. Returns mean, min, max NDVI."""
    # Demo mode — return realistic simulated values
    import random
    random.seed(hash(f"{lat}{lon}{date_str}") % 2**32)
    mean_ndvi = round(random.uniform(0.15, 0.65), 3)
    return {
        "mean_ndvi": mean_ndvi,
        "min_ndvi": round(max(-0.2, mean_ndvi - random.uniform(0.1, 0.25)), 3),
        "max_ndvi": round(min(0.9, mean_ndvi + random.uniform(0.1, 0.3)), 3),
        "vegetation_pct": round(max(0, (mean_ndvi - 0.2) / 0.6) * 100, 1),
    }
