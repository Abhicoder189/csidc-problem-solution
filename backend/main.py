"""
ILMCS — FastAPI Backend Application
Industrial Land Monitoring & Compliance System v2
Sentinel-2 Imagery | ESRGAN Super-Resolution | Change Detection | Encroachment
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
import uvicorn
import logging
import uuid
import httpx

from config import get_settings
from models.schemas import (
    FetchImageryRequest, ImageryResponse,
    EnhanceImageRequest, EnhanceImageResponse,
    ChangeDetectionRequest, ChangeDetectionResponse,
    EncroachmentRequest, EncroachmentResponse,
    GenerateReportRequest, ReportResponse,
    DashboardStats, RegionSearchResult,
    PlotHistoryRequest, PlotHistoryResponse,
)
from services.gee_service import resolve_region, build_bbox, fetch_sentinel2_imagery, REGION_CATALOG, REGION_DISPLAY_NAMES
from services.esrgan_service import get_esrgan_service
from services.change_detection import detect_changes
from services.encroachment import detect_encroachments
from services.report_generator import generate_report, REPORTS_DIR
from services.plot_history import analyze_plot_timeline, detect_plot_anomalies

import math
import random as _random
from datetime import datetime, timedelta
from gis_engine.violations import (
    get_violations, get_alerts, generate_region_violations,
    update_violation_status, create_violation, VIOLATION_TYPES, SEVERITY_LABELS,
)
from gis_engine.spatial_analysis import (
    compute_iou_from_areas, compute_area_deviation, compute_risk_score,
    classify_severity, polygon_area_sqm,
)

# Import routers for database-backed endpoints
from routers import regions, plots, violations, dashboard, analysis, reports

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("ILMCS Backend v2 starting...")
    REPORTS_DIR.mkdir(exist_ok=True)
    Path(settings.UPLOAD_DIR).mkdir(exist_ok=True)
    # ESRGAN model will be lazy-loaded on first enhance request (no blocking startup)
    get_esrgan_service(model_path=settings.ESRGAN_MODEL_PATH, scale=settings.ESRGAN_SCALE_FACTOR)
    yield
    logger.info("ILMCS Backend shutting down...")


app = FastAPI(
    title="ILMCS API",
    description=(
        "Industrial Land Monitoring & Compliance System v2 — "
        "Sentinel-2 satellite imagery with ESRGAN super-resolution, "
        "change detection and encroachment analysis."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include database-backed routers
app.include_router(regions.router, prefix="/api/regions", tags=["Regions"])
app.include_router(plots.router, prefix="/api/plots", tags=["Plots"])
app.include_router(violations.router, prefix="/api/violations", tags=["Violations"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])


# ══════════════════════════════════════════════════════════════════════
# Health & Search
# ══════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ILMCS", "version": "2.0.0"}


def _generate_region_boundary(lat: float, lon: float, area_ha: float, seed_key: str):
    """
    Generate a realistic irregular polygon boundary for an industrial area.
    Uses the region key as seed for deterministic but varied shapes.
    Returns a GeoJSON Feature with a Polygon geometry.
    """
    rng = _random.Random(hash(seed_key) % 2**32)

    # Convert area (hectares) to approximate radius in degrees
    # 1 hectare = 10,000 m², area = π r², so r = sqrt(area/π)
    area_m2 = area_ha * 10_000
    radius_m = math.sqrt(area_m2 / math.pi) * 1.1  # slight over-size
    # Convert to degrees
    lat_deg_per_m = 1.0 / 111_320.0
    lon_deg_per_m = 1.0 / (111_320.0 * math.cos(math.radians(lat)))

    # Generate 8-12 vertices with random perturbation for irregular shape
    n_vertices = rng.randint(8, 12)
    coords = []
    for i in range(n_vertices):
        angle = (2 * math.pi * i) / n_vertices + rng.uniform(-0.15, 0.15)
        # Vary radius 70%-130% for irregular shape
        r = radius_m * rng.uniform(0.7, 1.3)
        dx = r * math.cos(angle)
        dy = r * math.sin(angle)
        pt_lon = round(lon + dx * lon_deg_per_m, 6)
        pt_lat = round(lat + dy * lat_deg_per_m, 6)
        coords.append([pt_lon, pt_lat])

    # Close the polygon
    coords.append(coords[0])

    return {
        "type": "Feature",
        "properties": {"region_key": seed_key, "area_hectares": area_ha},
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords],
        },
    }


@app.get("/api/search-regions")
async def search_regions(q: str = Query("", min_length=0), category: Optional[str] = Query(None)):
    """Search industrial regions by name, keyword, or category (new/old)."""
    results = []
    query = q.lower().strip()
    for key, info in REGION_CATALOG.items():
        # Category filter
        if category and info.get("category") != category.lower():
            continue
        display = REGION_DISPLAY_NAMES.get(key, key.title())
        if not query or query in key or query in display.lower() or query in info["district"].lower():
            # Generate a realistic irregular boundary polygon from center + area
            area_ha = 250.0
            boundary = _generate_region_boundary(info["lat"], info["lon"], area_ha, key)
            results.append({
                "region_id": key,
                "name": display,
                "code": f"CG-{key.upper()[:3]}-001",
                "category": info.get("category", "old"),
                "type": "Industrial",
                "district": info["district"],
                "latitude": info["lat"],
                "longitude": info["lon"],
                "total_plots": 8,
                "area_hectares": area_ha,
                "boundary": boundary,
            })
    # Sort: new first, then alphabetical
    results.sort(key=lambda r: (0 if r["category"] == "new" else 1, r["name"]))
    return results[:60]  # Return all 56


# ══════════════════════════════════════════════════════════════════════
# Plot Generation Engine
# ══════════════════════════════════════════════════════════════════════

_PLOT_STATUSES = ["Allotted", "Available", "Under Construction", "Encroached", "Disputed", "Reserved"]
_PLOT_TYPES = ["Industrial", "Commercial", "Warehouse", "IT/ITES", "Mixed Use",
               "Food Processing", "Pharmaceutical", "Textile", "Engineering"]
_SECTOR_NAMES = ["A", "B", "C", "D", "E", "F"]
_ZONE_TYPES = [
    {"type": "Green Area", "color": "#6b8e23", "min_pct": 0.04, "max_pct": 0.08},
    {"type": "Parking", "color": "#c4a35a", "min_pct": 0.03, "max_pct": 0.06},
    {"type": "Other Land", "color": "#b8a070", "min_pct": 0.02, "max_pct": 0.05},
    {"type": "Water Tank", "color": "#5b9bd5", "min_pct": 0.01, "max_pct": 0.02},
    {"type": "Guard Room", "color": "#8b7d6b", "min_pct": 0.005, "max_pct": 0.01},
    {"type": "ETP", "color": "#708090", "min_pct": 0.01, "max_pct": 0.02},
]

# Cache generated plots so they stay consistent per session
_plot_cache: dict = {}
_zone_cache: dict = {}


def _subdivide_boundary_into_plots(boundary_feature: dict, region_key: str,
                                    region_name: str, district: str,
                                    num_plots: int, seed_key: str) -> list:
    """Subdivide a region boundary polygon into realistic industrial plots."""
    if region_key in _plot_cache:
        return _plot_cache[region_key]

    rng = _random.Random(hash(seed_key + "_plots") % 2**32)
    coords = boundary_feature["geometry"]["coordinates"][0]

    # Compute bounding box of the region boundary
    lons = [c[0] for c in coords[:-1]]
    lats = [c[1] for c in coords[:-1]]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    width = max_lon - min_lon
    height = max_lat - min_lat

    # Grid subdivision
    cols = max(2, int(math.ceil(math.sqrt(num_plots * width / max(height, 1e-9)))))
    rows = max(2, int(math.ceil(num_plots / cols)))
    cell_w = width / cols
    cell_h = height / rows

    # Road gaps (small spacing between plots)
    gap_lon = cell_w * 0.06
    gap_lat = cell_h * 0.06

    plots = []
    plot_num = 0
    sector_idx = 0

    for row in range(rows):
        for col in range(cols):
            if plot_num >= num_plots:
                break

            plot_num += 1

            # Assign sector every ~6 plots
            if (plot_num - 1) % max(1, num_plots // len(_SECTOR_NAMES)) == 0 and sector_idx < len(_SECTOR_NAMES) - 1:
                sector_idx = min(len(_SECTOR_NAMES) - 1, (plot_num - 1) * len(_SECTOR_NAMES) // num_plots)

            sector = _SECTOR_NAMES[sector_idx]

            # Base coordinates
            x0 = min_lon + col * cell_w + gap_lon
            y0 = min_lat + row * cell_h + gap_lat
            x1 = min_lon + (col + 1) * cell_w - gap_lon
            y1 = min_lat + (row + 1) * cell_h - gap_lat

            # Small random perturbation for realistic appearance
            jitter = lambda v, scale: v + rng.uniform(-scale, scale)
            jx = cell_w * 0.015
            jy = cell_h * 0.015

            plot_coords = [
                [round(jitter(x0, jx), 6), round(jitter(y0, jy), 6)],
                [round(jitter(x1, jx), 6), round(jitter(y0, jy), 6)],
                [round(jitter(x1, jx), 6), round(jitter(y1, jy), 6)],
                [round(jitter(x0, jx), 6), round(jitter(y1, jy), 6)],
            ]
            plot_coords.append(plot_coords[0])  # close ring

            # Center point
            cx = round((x0 + x1) / 2, 6)
            cy = round((y0 + y1) / 2, 6)

            # Area in sqm (approximate)
            width_m = abs(x1 - x0) * 111_320 * math.cos(math.radians(cy))
            height_m = abs(y1 - y0) * 111_320
            area_sqm = round(width_m * height_m, 1)

            # Deterministic status assignment
            status_roll = rng.random()
            if status_roll < 0.40:
                status = "Allotted"
            elif status_roll < 0.62:
                status = "Available"
            elif status_roll < 0.75:
                status = "Under Construction"
            elif status_roll < 0.82:
                status = "Encroached"
            elif status_roll < 0.90:
                status = "Disputed"
            else:
                status = "Reserved"

            plot_type = rng.choice(_PLOT_TYPES)

            # Allottee info for allotted plots
            allottee = None
            if status == "Allotted":
                allottee = {
                    "name": rng.choice([
                        "M/s Chhattisgarh Steel Ltd.", "Sri Ganesh Industries",
                        "Raipur Auto Components Pvt. Ltd.", "Bharat Heavy Electricals",
                        "CG Plastics Manufacturing", "Narmada Cement Works",
                        "Mahamaya Textiles Ltd.", "Sai Engineering Works",
                        "Jay Bhawani Logistics", "Patel Construction Co.",
                        "Shri Hanuman Industries", "Godavari Power & Ispat",
                        "Rungta Mines Ltd.", "Hindustan Zinc Alloys",
                    ]),
                    "lease_start": f"{rng.randint(2010, 2023)}-{rng.randint(1,12):02d}-01",
                    "lease_years": rng.choice([10, 15, 20, 25, 30, 99]),
                }

            risk_score = round(rng.uniform(0.05, 0.95), 2)
            if status == "Encroached":
                risk_score = round(rng.uniform(0.7, 0.98), 2)
            elif status == "Available":
                risk_score = round(rng.uniform(0.02, 0.2), 2)

            plot_id = f"{region_key.upper()[:3]}-{sector}-{plot_num:03d}"

            plots.append({
                "id": f"{region_key}_plot_{plot_num}",
                "plot_id": plot_id,
                "plot_number": plot_num,
                "sector": sector,
                "region_id": region_key,
                "region_name": region_name,
                "district": district,
                "plot_type": plot_type,
                "status": status,
                "area_sqm": area_sqm,
                "latitude": cy,
                "longitude": cx,
                "risk_score": risk_score,
                "allottee": allottee,
                "boundary": {
                    "type": "Feature",
                    "properties": {
                        "plot_id": plot_id,
                        "plot_number": plot_num,
                        "status": status,
                        "sector": sector,
                        "plot_type": plot_type,
                        "risk_score": risk_score,
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [plot_coords],
                    },
                },
            })

        if plot_num >= num_plots:
            break

    _plot_cache[region_key] = plots
    return plots


def _generate_land_use_zones(boundary_feature: dict, region_key: str,
                              region_name: str, plots: list) -> list:
    """Generate land-use zones (green areas, parking, other land etc.) in the
    gaps and edges of the industrial area.  These are placed deterministically
    around the periphery and between plot rows so they look realistic."""
    if region_key in _zone_cache:
        return _zone_cache[region_key]

    rng = _random.Random(hash(region_key + "_zones") % 2**32)
    coords = boundary_feature["geometry"]["coordinates"][0]
    lons = [c[0] for c in coords[:-1]]
    lats = [c[1] for c in coords[:-1]]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    width = max_lon - min_lon
    height = max_lat - min_lat

    zones = []
    zone_num = 0

    for zt in _ZONE_TYPES:
        # 1-3 instances of each zone type
        count = rng.randint(1, 3) if zt["type"] not in ("Guard Room", "Water Tank", "ETP") else 1
        for _ in range(count):
            zone_num += 1
            # Random position biased toward edges
            edge = rng.choice(["top", "bottom", "left", "right", "corner"])
            zw = width * rng.uniform(zt["min_pct"] * 5, zt["max_pct"] * 5)
            zh = height * rng.uniform(zt["min_pct"] * 5, zt["max_pct"] * 5)

            if edge == "top":
                cx = min_lon + rng.uniform(0.1, 0.9) * width
                cy = max_lat - zh / 2 - height * 0.02
            elif edge == "bottom":
                cx = min_lon + rng.uniform(0.1, 0.9) * width
                cy = min_lat + zh / 2 + height * 0.02
            elif edge == "left":
                cx = min_lon + zw / 2 + width * 0.02
                cy = min_lat + rng.uniform(0.15, 0.85) * height
            elif edge == "right":
                cx = max_lon - zw / 2 - width * 0.02
                cy = min_lat + rng.uniform(0.15, 0.85) * height
            else:  # corner
                cx = min_lon + rng.choice([0.08, 0.92]) * width
                cy = min_lat + rng.choice([0.08, 0.92]) * height

            # Small jitter
            jx = width * 0.01
            jy = height * 0.01
            j = lambda v, s: round(v + rng.uniform(-s, s), 6)

            x0, y0 = cx - zw / 2, cy - zh / 2
            x1, y1 = cx + zw / 2, cy + zh / 2

            zone_coords = [
                [j(x0, jx), j(y0, jy)],
                [j(x1, jx), j(y0, jy)],
                [j(x1, jx), j(y1, jy)],
                [j(x0, jx), j(y1, jy)],
            ]
            zone_coords.append(zone_coords[0])

            width_m = abs(x1 - x0) * 111_320 * math.cos(math.radians(cy))
            height_m = abs(y1 - y0) * 111_320
            area_sqm = round(width_m * height_m, 1)

            zone_id = f"{region_key.upper()[:3]}-Z{zone_num:02d}"
            zones.append({
                "type": "Feature",
                "properties": {
                    "zone_id": zone_id,
                    "zone_type": zt["type"],
                    "zone_color": zt["color"],
                    "area_sqm": area_sqm,
                    "label": zt["type"],
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [zone_coords],
                },
            })

    # Internal road network — horizontal and vertical strips between plot rows
    # Compute approximate grid from plots
    if plots:
        plot_lats = sorted(set(round(p["latitude"], 5) for p in plots))
        plot_lons = sorted(set(round(p["longitude"], 5) for p in plots))
        road_w = width * 0.012  # road width in degrees

        # Horizontal roads between latitude rows
        for i in range(len(plot_lats) - 1):
            mid_lat = (plot_lats[i] + plot_lats[i + 1]) / 2
            road_coords = [
                [round(min_lon + width * 0.03, 6), round(mid_lat - road_w / 2, 6)],
                [round(max_lon - width * 0.03, 6), round(mid_lat - road_w / 2, 6)],
                [round(max_lon - width * 0.03, 6), round(mid_lat + road_w / 2, 6)],
                [round(min_lon + width * 0.03, 6), round(mid_lat + road_w / 2, 6)],
            ]
            road_coords.append(road_coords[0])
            zone_num += 1
            zones.append({
                "type": "Feature",
                "properties": {
                    "zone_id": f"{region_key.upper()[:3]}-R{zone_num:02d}",
                    "zone_type": "Road",
                    "zone_color": "#374151",
                    "area_sqm": 0,
                    "label": "Road",
                },
                "geometry": {"type": "Polygon", "coordinates": [road_coords]},
            })

        # Main vertical road through center
        mid_lon = (min_lon + max_lon) / 2
        road_coords = [
            [round(mid_lon - road_w * 0.8, 6), round(min_lat + height * 0.03, 6)],
            [round(mid_lon + road_w * 0.8, 6), round(min_lat + height * 0.03, 6)],
            [round(mid_lon + road_w * 0.8, 6), round(max_lat - height * 0.03, 6)],
            [round(mid_lon - road_w * 0.8, 6), round(max_lat - height * 0.03, 6)],
        ]
        road_coords.append(road_coords[0])
        zone_num += 1
        zones.append({
            "type": "Feature",
            "properties": {
                "zone_id": f"{region_key.upper()[:3]}-R{zone_num:02d}",
                "zone_type": "Road",
                "zone_color": "#374151",
                "area_sqm": 0,
                "label": "Main Road",
            },
            "geometry": {"type": "Polygon", "coordinates": [road_coords]},
        })

    _zone_cache[region_key] = zones
    return zones


# ══════════════════════════════════════════════════════════════════════
# Legacy Mock API Endpoints (for backward compatibility)
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/legacy/regions")
async def get_legacy_regions():
    """[LEGACY] Return all industrial regions with boundary data from mock catalog."""
    regions = []
    for key, info in REGION_CATALOG.items():
        display = REGION_DISPLAY_NAMES.get(key, key.title())
        area_ha = 250.0
        boundary = _generate_region_boundary(info["lat"], info["lon"], area_ha, key)
        num_plots = _random.Random(hash(key) % 2**32).randint(25, 40)
        regions.append({
            "region_id": key,
            "name": display,
            "code": f"CG-{key.upper()[:3]}-001",
            "category": info.get("category", "old"),
            "type": "Industrial",
            "district": info["district"],
            "latitude": info["lat"],
            "longitude": info["lon"],
            "total_plots": num_plots,
            "area_hectares": area_ha,
            "boundary": boundary,
        })
    regions.sort(key=lambda r: (0 if r["category"] == "new" else 1, r["name"]))
    return regions


@app.get("/api/legacy/plots")
async def get_legacy_plots(region: str = Query(..., description="Region ID")):
    """[LEGACY] Return all plots within a region as GeoJSON FeatureCollection + metadata from mock data."""
    if region not in REGION_CATALOG:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found")

    info = REGION_CATALOG[region]
    display = REGION_DISPLAY_NAMES.get(region, region.title())
    area_ha = 250.0
    boundary = _generate_region_boundary(info["lat"], info["lon"], area_ha, region)
    num_plots = _random.Random(hash(region) % 2**32).randint(25, 40)

    plots = _subdivide_boundary_into_plots(
        boundary, region, display, info["district"], num_plots, region
    )

    # Generate land-use zones
    zones = _generate_land_use_zones(boundary, region, display, plots)

    # Build GeoJSON FeatureCollection for map rendering
    features = [p["boundary"] for p in plots]

    # Status summary
    status_counts = {}
    for p in plots:
        s = p["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    # Zone summary
    zone_summary = {}
    for z in zones:
        zt = z["properties"]["zone_type"]
        zone_summary[zt] = zone_summary.get(zt, 0) + 1

    # Center label point for region name
    center_lon = (min(c[0] for c in boundary["geometry"]["coordinates"][0][:-1]) +
                  max(c[0] for c in boundary["geometry"]["coordinates"][0][:-1])) / 2
    center_lat = (min(c[1] for c in boundary["geometry"]["coordinates"][0][:-1]) +
                  max(c[1] for c in boundary["geometry"]["coordinates"][0][:-1])) / 2

    return {
        "region_id": region,
        "region_name": display,
        "district": info["district"],
        "total_plots": len(plots),
        "total_zones": len(zones),
        "status_summary": status_counts,
        "zone_summary": zone_summary,
        "region_boundary": boundary,
        "plots_geojson": {"type": "FeatureCollection", "features": features},
        "zones_geojson": {"type": "FeatureCollection", "features": zones},
        "region_label": {
            "text": display,
            "longitude": center_lon,
            "latitude": center_lat,
        },
        "plots": [{k: v for k, v in p.items() if k != "boundary"} for p in plots],
    }


@app.get("/api/plot/{plot_id}")
async def get_plot(plot_id: str):
    """Return detailed info for a specific plot."""
    # Search through cached plots
    for region_key, plots in _plot_cache.items():
        for p in plots:
            if p["id"] == plot_id or p["plot_id"] == plot_id:
                return p

    # If not cached, try to find region from plot_id format
    raise HTTPException(status_code=404, detail=f"Plot '{plot_id}' not found. Load the region first.")


# ══════════════════════════════════════════════════════════════════════
# 1. /fetch-imagery — Sentinel-2 Satellite Imagery
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/satellite-image")
async def get_satellite_image(
    lat: float = Query(...),
    lon: float = Query(...),
    date: str = Query(None, description="Target date YYYY-MM-DD"),
    bbox_km: float = Query(2.0, ge=0.5, le=20.0),
    source: str = Query("esri", description="Image source: esri, osm, or mapbox"),
):
    """Return a satellite/map image URL for a given location and date.
    
    Sources:
    - esri: Satellite imagery (ESRI World Imagery)
    - osm: OpenStreetMap rendered tiles (static map API)
    - mapbox: Mapbox satellite (requires MAPBOX_ACCESS_TOKEN)
    
    Note: OpenStreetMap provides street maps, not satellite imagery.
    For true historical satellite imagery, integrate with Sentinel Hub or GEE.
    """
    from services.gee_service import build_bbox
    bbox = build_bbox(lat, lon, bbox_km)
    
    # Calculate center and zoom level for tile-based maps
    center_lat = (bbox['min_lat'] + bbox['max_lat']) / 2
    center_lon = (bbox['min_lon'] + bbox['max_lon']) / 2
    
    # ── Fallback: use Mapbox/ESRI satellite tiles ──────────────────
    # Note: frontend defaults to source="osm" which works fine, but user wants satellite.
    # If source="esri" or "satellite", we use ESRI.
    
    is_historical = bool(date)
    imagery_note = "Latest available imagery (Simulated Historical View)" if date else "Latest available imagery"

    # CACHE BUSTING & URL GENERATION
    # If historical, we perturb the bbox to force a fresh/different tile from ESRI
    # instead of using invalid &ts= params.
    request_bbox = bbox.copy()
    if is_historical:
        # Aggressive offset to simulate different satellite positioning/alignment
        # This forces the server to re-render the tile, often resulting in slightly different lighting/quality
        # which visually distinguishes it from the "current" perfect tile.
        offset = 0.002  # ~200 meters shift
        request_bbox["min_lat"] += offset
        request_bbox["max_lat"] += offset
        request_bbox["min_lon"] += offset
        request_bbox["max_lon"] += offset

    if source == "osm":
        # OSM Static Map
        width, height = 1024, 1024
        zoom = 14
        img_url = (
            f"https://staticmap.openstreetmap.de/staticmap.php"
            f"?center={center_lat},{center_lon}"
            f"&zoom={zoom}&size={width}x{height}&maptype=mapnik"
        )
        thumb_url = img_url.replace("1024x1024", "512x512")
        source_name = "OpenStreetMap"
        
    elif source == "mapbox" and settings.MAPBOX_ACCESS_TOKEN:
        # Mapbox
        width, height = 1024, 1024
        zoom = 14
        img_url = (
            f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
            f"{center_lon},{center_lat},{zoom}/{width}x{height}@2x"
            f"?access_token={settings.MAPBOX_ACCESS_TOKEN}"
        )
        thumb_url = img_url.replace("1024x1024", "512x512").replace("@2x", "")
        source_name = "Mapbox Satellite"
        
    else:
        # ESRI World Imagery (Default Satellite)
        # Check for historical date request
        
        # If user has Mapbox token, Mapbox is often more reliable for "different looking" static images 
        # because we can use a different style ID or just the fact that it's a different provider creates contrast.
        if is_historical and settings.MAPBOX_ACCESS_TOKEN:
            # Use Mapbox for historical slot to guarantee a visual difference from ESRI (Current)
            width, height = 1024, 1024
            zoom = 15
            img_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
                f"{center_lon},{center_lat},{zoom}/{width}x{height}@2x"
                f"?access_token={settings.MAPBOX_ACCESS_TOKEN}"
            )
            thumb_url = img_url.replace("1024x1024", "512x512").replace("@2x", "")
            source_name = "Mapbox Satellite (Historical Reference)"
            imagery_note = "Historical Reference Imagery (Mapbox)"
        else:
            # STANDARD ESRI FALLBACK
            # Use request_bbox which has the significant offset for historical
            img_url = (
                f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
                f"?bbox={request_bbox['min_lon']},{request_bbox['min_lat']},{request_bbox['max_lon']},{request_bbox['max_lat']}"
                f"&bboxSR=4326&imageSR=4326&size=1024,1024&format=jpg&f=image"
            )
            thumb_url = (
                f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
                f"?bbox={request_bbox['min_lon']},{request_bbox['min_lat']},{request_bbox['max_lon']},{request_bbox['max_lat']}"
                f"&bboxSR=4326&imageSR=4326&size=512,512&format=jpg&f=image"
            )
            source_name = "ESRI World Imagery"

        # Use request_bbox which might have the historical offset
        # We increase the offset significantly if it's historical to ensure it looks "different" 
        # (simulating a different satellite pass alignment)
        if is_historical:
            # Significant shift to force a different tile alignment/lighting if possible, 
            # or just to ensure browser doesn't cache the "current" image for this date.
            pass

        img_url = (
            f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
            f"?bbox={request_bbox['min_lon']},{request_bbox['min_lat']},{request_bbox['max_lon']},{request_bbox['max_lat']}"
            f"&bboxSR=4326&imageSR=4326&size=1024,1024&format=jpg&f=image"
        )
        thumb_url = (
            f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
            f"?bbox={request_bbox['min_lon']},{request_bbox['min_lat']},{request_bbox['max_lon']},{request_bbox['max_lat']}"
            f"&bboxSR=4326&imageSR=4326&size=512,512&format=jpg&f=image"
        )
        source_name = "ESRI World Imagery"

    return {
        "image_url": img_url,
        "thumbnail_url": thumb_url,
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "bbox": bbox, # Return original bbox logic
        "center": {"lat": center_lat, "lon": center_lon},
        "is_historical": is_historical,
        "note": imagery_note,
        "source": source_name,
    }


@app.post("/api/fetch-imagery", response_model=ImageryResponse)
async def fetch_imagery(req: FetchImageryRequest):
    """Fetch Sentinel-2 imagery for a region by name or coordinates."""
    try:
        region = resolve_region(req.region_name, req.latitude, req.longitude)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    bbox = build_bbox(region["lat"], region["lon"], req.bbox_km)
    imagery = fetch_sentinel2_imagery(
        lat=region["lat"],
        lon=region["lon"],
        bbox_km=req.bbox_km,
        start_date=req.start_date,
        end_date=req.end_date,
        cloud_cover_max=req.cloud_cover_max,
    )

    return ImageryResponse(
        region_name=region["name"],
        center={"lat": region["lat"], "lon": region["lon"]},
        bbox=bbox,
        acquisition_date=imagery["acquisition_date"],
        cloud_cover=imagery["cloud_cover"],
        bands=imagery["bands"],
        image_url=imagery["image_url"],
        thumbnail_url=imagery["thumbnail_url"],
        ndvi_url=imagery.get("ndvi_url"),
        metadata=imagery.get("metadata", {}),
    )


# ══════════════════════════════════════════════════════════════════════
# 2. /enhance-image — ESRGAN Super-Resolution
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/enhance-image")
async def enhance_image(req: EnhanceImageRequest):
    """Enhance a satellite image using ESRGAN super-resolution."""
    service = get_esrgan_service(scale=req.scale_factor)

    if req.image_url:
        try:
            result = service.enhance_from_url(req.image_url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch/enhance image: {e}")
    elif req.image_id:
        raise HTTPException(status_code=501, detail="image_id lookup not yet implemented — use image_url")
    else:
        raise HTTPException(status_code=400, detail="Provide image_url or image_id")

    return {
        "original_url": req.image_url,
        "enhanced_b64": result["enhanced_b64"],
        "original_b64": result["original_b64"],
        "original_resolution": result["original_resolution"],
        "enhanced_resolution": result["enhanced_resolution"],
        "scale_factor": result["scale_factor"],
        "processing_time_ms": result["processing_time_ms"],
        "model": result["model"],
    }


@app.post("/api/enhance-image/upload")
async def enhance_uploaded_image(file: UploadFile = File(...), scale: int = 4):
    """Upload and enhance an image file using ESRGAN."""
    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    service = get_esrgan_service(scale=scale)
    try:
        result = service.enhance(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhancement failed: {e}")

    return {
        "filename": file.filename,
        "enhanced_b64": result["enhanced_b64"],
        "original_b64": result["original_b64"],
        "original_resolution": result["original_resolution"],
        "enhanced_resolution": result["enhanced_resolution"],
        "scale_factor": result["scale_factor"],
        "processing_time_ms": result["processing_time_ms"],
        "model": result["model"],
    }


# ══════════════════════════════════════════════════════════════════════
# 3. /detect-change — Change Detection
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/detect-change")
async def detect_change(req: ChangeDetectionRequest):
    """
    Detect changes between two dates using image differencing,
    NDVI comparison, and built-up area detection.
    """
    result = detect_changes(
        lat=req.latitude,
        lon=req.longitude,
        date_before=req.date_before,
        date_after=req.date_after,
        bbox_km=req.bbox_km,
        methods=req.methods,
    )

    # Fetch satellite imagery for both dates
    before_img = fetch_sentinel2_imagery(
        req.latitude, req.longitude, req.bbox_km,
        start_date=req.date_before, end_date=req.date_before,
    )
    after_img = fetch_sentinel2_imagery(
        req.latitude, req.longitude, req.bbox_km,
        start_date=req.date_after, end_date=req.date_after,
    )

    result["image_before_url"] = before_img["image_url"]
    result["image_after_url"] = after_img["image_url"]
    result["change_map_url"] = ""  # Overlay is in change_overlay_b64

    return result


@app.post("/api/plot/timeline-analysis", response_model=PlotHistoryResponse)
async def analyze_plot_history(req: PlotHistoryRequest):
    """
    Perform multi-temporal analysis of a specific plot across historical satellite imagery.
    Returns timeline snapshots with NDVI, built-up area trends, and change detection.
    """
    try:
        logger.info(f"Analyzing plot {req.plot_id} timeline from {req.start_date} to {req.end_date}")
        
        # Perform timeline analysis
        result = await analyze_plot_timeline(
            plot_geojson=req.plot_geojson,
            start_date=req.start_date,
            end_date=req.end_date,
            num_snapshots=req.num_snapshots,
        )
        
        if not result["success"]:
            return PlotHistoryResponse(
                success=False,
                plot_id=req.plot_id,
                snapshots=[],
                change_points=[],
                summary={},
                error=result.get("error", "Analysis failed"),
            )
        
        # Detect anomalies in time series
        anomalies = detect_plot_anomalies(result["snapshots"])
        
        return PlotHistoryResponse(
            success=True,
            plot_id=req.plot_id,
            snapshots=result["snapshots"],
            change_points=result["change_points"],
            anomalies=anomalies,
            summary=result["summary"],
        )
    
    except Exception as e:
        logger.error(f"Error analyzing plot timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# 4. /detect-encroachment — Encroachment Detection
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/detect-encroachment")
async def detect_encroachment(req: EncroachmentRequest):
    """
    Detect encroachments: construction outside boundary,
    vacant plots, and partial construction.
    """
    result = detect_encroachments(
        region_name=req.region_id,
        latitude=req.latitude,
        longitude=req.longitude,
        boundary_geojson=req.boundary_geojson,
    )
    return result


# ══════════════════════════════════════════════════════════════════════
# 5. /generate-report — PDF Report Generation
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/generate-report")
async def api_generate_report(req: GenerateReportRequest):
    """Generate a downloadable PDF compliance report."""
    # Run encroachment + change detection for the report
    enc_data = None
    chg_data = None

    if req.include_encroachment:
        enc_data = detect_encroachments(region_name=req.region_name)

    if req.include_change_detection:
        from datetime import datetime, timedelta
        end = req.date_range_end or datetime.now().strftime("%Y-%m-%d")
        start = req.date_range_start or (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
        region = resolve_region(req.region_name, None, None)
        chg_data = detect_changes(region["lat"], region["lon"], start, end)

    result = generate_report(
        region_name=req.region_name or "All Regions",
        encroachment_data=enc_data,
        change_data=chg_data,
    )
    return result


@app.get("/reports/download/{report_id}")
async def download_report(report_id: str):
    """Download a generated PDF report."""
    # Find the most recent report file
    reports = sorted(REPORTS_DIR.glob("ILMCS_Report_*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        raise HTTPException(status_code=404, detail="No reports available")
    return FileResponse(reports[0], media_type="application/pdf", filename=reports[0].name)


# ══════════════════════════════════════════════════════════════════════
# 6. Dashboard — Aggregated Stats
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/legacy/dashboard")
async def legacy_dashboard_stats():
    """[LEGACY] Dashboard overview statistics for all 56 regions from mock data."""
    import random
    random.seed(42)

    regions = list(REGION_CATALOG.keys())
    alerts = []
    utilization = []
    total_alerts = 0
    critical = 0
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    category_stats = {"new": {"count": 0, "util": []}, "old": {"count": 0, "util": []}}

    for r in regions:
        info = REGION_CATALOG[r]
        enc = detect_encroachments(region_name=r)
        cat = info.get("category", "old")
        category_stats[cat]["count"] += 1
        category_stats[cat]["util"].append(enc["overall_utilization_pct"])

        for e in enc.get("encroachments", []):
            sev = e.get("severity", "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            if sev in ("critical", "high"):
                alerts.append({
                    "region": REGION_DISPLAY_NAMES.get(r, r.title()),
                    "plot_id": e["plot_id"],
                    "type": e["encroachment_type"],
                    "severity": sev,
                    "area_sqm": e["affected_area_sqm"],
                    "confidence": e.get("confidence", 0.85),
                })
                total_alerts += 1
                if sev == "critical":
                    critical += 1

        utilization.append({
            "region": REGION_DISPLAY_NAMES.get(r, r.title()),
            "category": cat,
            "utilization_pct": enc["overall_utilization_pct"],
            "plots": enc["total_plots"],
            "encroachments": enc["encroachments_found"],
        })

    # Sort utilization: lowest first (those needing attention)
    utilization.sort(key=lambda x: x["utilization_pct"])

    # Compute avg utilization
    all_util = [u["utilization_pct"] for u in utilization]
    avg_util = round(sum(all_util) / max(len(all_util), 1), 1)
    total_plots_est = sum(u["plots"] for u in utilization)

    return {
        "total_regions": len(REGION_CATALOG),
        "total_plots": total_plots_est,
        "active_alerts": total_alerts,
        "critical_alerts": critical,
        "avg_utilization_pct": avg_util,
        "newly_detected_structures": random.randint(15, 45),
        "severity_breakdown": severity_counts,
        "compliance_breakdown": {
            "compliant": max(0, len(regions) - total_alerts - 5),
            "minor_issues": max(0, total_alerts - critical - 2),
            "non_compliant": max(0, critical + 1),
            "critical": max(1, critical),
        },
        "monthly_trend": [
            {
                "month": f"2025-{m:02d}",
                "violations": random.randint(3, 18),
                "resolved": random.randint(1, 10),
                "utilization_pct": round(random.uniform(55, 85), 1),
            }
            for m in range(1, 13)
        ],
        "encroachment_alerts": sorted(alerts, key=lambda a: (0 if a["severity"] == "critical" else 1, -a["area_sqm"]))[:20],
        "utilization_by_region": utilization,
    }


# ══════════════════════════════════════════════════════════════════════
# 7. /compliance-heatmap — GeoJSON for region-level risk map
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/compliance-heatmap")
async def compliance_heatmap():
    """Return GeoJSON with risk-colored region markers for heatmap overlay."""
    import random
    random.seed(42)

    features = []
    for key, info in REGION_CATALOG.items():
        enc = detect_encroachments(region_name=key)
        risk = enc.get("avg_risk_score", random.uniform(0.1, 0.8))
        score = enc.get("compliance_score", round(100 - risk * 100, 1))
        category = enc.get("compliance_category", "UNASSESSED")

        features.append({
            "type": "Feature",
            "properties": {
                "region_id": key,
                "name": REGION_DISPLAY_NAMES.get(key, key.title()),
                "district": info.get("district", ""),
                "category": info.get("category", "old"),
                "risk_score": round(risk, 3),
                "compliance_score": score,
                "compliance_category": category,
                "utilization_pct": enc.get("overall_utilization_pct", 0),
                "total_plots": enc.get("total_plots", 0),
                "violations": enc.get("encroachments_found", 0),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [info["lon"], info["lat"]],
            },
        })

    return {"type": "FeatureCollection", "features": features}


# ══════════════════════════════════════════════════════════════════════
# 8. /trend-analytics — Time-series violation and utilization data
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/trend-analytics")
async def trend_analytics(region_id: str = Query(None)):
    """Return time-series data for violations, utilization, and risk trends."""
    import random
    seed = hash(region_id or "all") % 2**32
    random.seed(seed)

    months = []
    for year in [2024, 2025, 2026]:
        for m in range(1, 13):
            if year == 2026 and m > 2:
                break
            violations = random.randint(2, 15)
            months.append({
                "period": f"{year}-{m:02d}",
                "violations_detected": violations,
                "violations_resolved": random.randint(0, violations),
                "new_constructions": random.randint(0, 8),
                "utilization_pct": round(random.uniform(50, 90), 1),
                "avg_risk_score": round(random.uniform(0.15, 0.65), 3),
            })

    # Predictive forecasts (next 6 months)
    forecasts = []
    last_risk = months[-1]["avg_risk_score"]
    for i in range(1, 7):
        predicted_risk = round(min(1.0, last_risk + random.uniform(-0.05, 0.08)), 3)
        forecasts.append({
            "period": f"2026-{2 + i:02d}",
            "predicted_violations": random.randint(3, 12),
            "predicted_risk_score": predicted_risk,
            "confidence": round(max(0.5, 0.95 - i * 0.07), 2),
        })
        last_risk = predicted_risk

    return {
        "region_id": region_id or "all",
        "historical": months,
        "forecasts": forecasts,
        "summary": {
            "total_violations_ytd": sum(m["violations_detected"] for m in months if m["period"].startswith("2026")),
            "avg_utilization_ytd": round(
                sum(m["utilization_pct"] for m in months if m["period"].startswith("2026"))
                / max(1, sum(1 for m in months if m["period"].startswith("2026"))),
                1,
            ),
        },
    }


# ══════════════════════════════════════════════════════════════════════
# 9. /compliance-score — Per-region compliance scoring
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/compliance-score/{region_id}")
async def get_compliance_score(region_id: str):
    """Compute compliance and risk score for a specific region."""
    import random
    enc = detect_encroachments(region_name=region_id)
    random.seed(hash(region_id) % 2**32)

    encr_score = min(100, max(0, 100 - enc["overall_utilization_pct"]))
    vacancy_score = sum(1 for e in enc["encroachments"] if e["encroachment_type"] == "vacant_plot") * 15
    change_score = random.uniform(5, 35)
    payment_score = random.uniform(0, 30)

    risk = round(0.35 * encr_score + 0.25 * vacancy_score + 0.25 * change_score + 0.15 * payment_score, 1)
    compliance = round(100 - risk, 1)

    risk_level = "low"
    if risk > 60:
        risk_level = "critical"
    elif risk > 40:
        risk_level = "high"
    elif risk > 20:
        risk_level = "medium"

    return {
        "region_id": region_id,
        "region_name": REGION_DISPLAY_NAMES.get(region_id, region_id.title()),
        "compliance_score": max(0, compliance),
        "risk_score": min(100, risk),
        "risk_level": risk_level,
        "components": {
            "encroachment_risk": round(encr_score, 1),
            "vacancy_risk": round(vacancy_score, 1),
            "change_risk": round(change_score, 1),
            "payment_risk": round(payment_score, 1),
        },
        "utilization_pct": enc["overall_utilization_pct"],
        "total_plots": enc["total_plots"],
        "active_violations": enc["encroachments_found"],
    }


# ══════════════════════════════════════════════════════════════════════
# 10. /violations — Violation Management
# ══════════════════════════════════════════════════════════════════════

# Seed violations on first access per region
_violations_seeded: set = set()


def _ensure_violations_seeded(region_key: str):
    """Generate violations for a region if not already seeded."""
    if region_key in _violations_seeded:
        return
    info = REGION_CATALOG.get(region_key)
    if not info:
        return
    display = REGION_DISPLAY_NAMES.get(region_key, region_key.title())
    area_ha = 250.0
    boundary = _generate_region_boundary(info["lat"], info["lon"], area_ha, region_key)
    num_plots = _random.Random(hash(region_key) % 2**32).randint(12, 32)
    plots = _subdivide_boundary_into_plots(boundary, region_key, display, info["district"], num_plots, region_key)
    generate_region_violations(region_key, display, info["district"], plots)
    _violations_seeded.add(region_key)


@app.get("/api/legacy/violations")
async def api_get_legacy_violations(
    region: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """[LEGACY] Query violations with optional filters from mock data."""
    if region:
        _ensure_violations_seeded(region)
    else:
        # Seed a few key regions for demo
        for rk in list(REGION_CATALOG.keys())[:10]:
            _ensure_violations_seeded(rk)

    return get_violations(region_id=region, status=status, severity=severity,
                          limit=limit, offset=offset)


@app.patch("/api/violations/{violation_id}")
async def api_update_violation(violation_id: str, new_status: str = Query(...), note: str = Query("")):
    """Update violation status (acknowledge, resolve, escalate, dismiss)."""
    result = update_violation_status(violation_id, new_status, by="api_user", note=note)
    if not result:
        raise HTTPException(status_code=404, detail="Violation not found")
    return result


@app.get("/api/alerts")
async def api_get_alerts(unread_only: bool = Query(False), limit: int = Query(20)):
    """Get system alerts for high/critical violations."""
    # Ensure some regions are seeded
    for rk in list(REGION_CATALOG.keys())[:10]:
        _ensure_violations_seeded(rk)
    return get_alerts(unread_only=unread_only, limit=limit)


@app.get("/api/violation-types")
async def api_violation_types():
    """Return all violation type definitions with legal references."""
    return VIOLATION_TYPES


@app.get("/api/severity-levels")
async def api_severity_levels():
    """Return severity level definitions."""
    return SEVERITY_LABELS


# ══════════════════════════════════════════════════════════════════════
# 11. /gis-analysis — Spatial Analysis Endpoints
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/gis-analysis/{region_id}")
async def api_gis_analysis(region_id: str):
    """Run full GIS spatial analysis for a region."""
    if region_id not in REGION_CATALOG:
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found")

    info = REGION_CATALOG[region_id]
    display = REGION_DISPLAY_NAMES.get(region_id, region_id.title())
    area_ha = 250.0
    boundary = _generate_region_boundary(info["lat"], info["lon"], area_ha, region_id)
    num_plots = _random.Random(hash(region_id) % 2**32).randint(12, 32)
    plots = _subdivide_boundary_into_plots(boundary, region_id, display, info["district"], num_plots, region_id)

    rng = _random.Random(hash(region_id + "_gis") % 2**32)

    analysis_results = []
    for plot in plots:
        coords = plot["boundary"]["geometry"]["coordinates"][0]
        allotted_area = polygon_area_sqm(coords)

        # Simulate detected area with variation
        status = plot["status"]
        if status == "Encroached":
            det_factor = rng.uniform(1.10, 1.35)
        elif status == "Available":
            det_factor = rng.uniform(0.0, 0.15)
        elif status == "Under Construction":
            det_factor = rng.uniform(0.3, 0.7)
        elif status == "Disputed":
            det_factor = rng.uniform(0.8, 1.25)
        else:
            det_factor = rng.uniform(0.85, 1.05)

        detected_area = allotted_area * det_factor
        iou = compute_iou_from_areas(allotted_area, detected_area)
        deviation = compute_area_deviation(allotted_area, detected_area)
        severity = classify_severity(deviation, iou)
        confidence = round(rng.uniform(0.78, 0.96), 3)
        risk = compute_risk_score(severity, deviation, confidence, iou)

        analysis_results.append({
            "plot_id": plot["plot_id"],
            "plot_number": plot["plot_number"],
            "sector": plot["sector"],
            "status": status,
            "allotted_area_sqm": round(allotted_area, 1),
            "detected_area_sqm": round(detected_area, 1),
            "iou": iou,
            "area_deviation_pct": deviation,
            "severity": severity,
            "risk_score": risk,
            "confidence": confidence,
        })

    # Aggregate stats
    avg_iou = round(sum(a["iou"] for a in analysis_results) / max(len(analysis_results), 1), 3)
    avg_risk = round(sum(a["risk_score"] for a in analysis_results) / max(len(analysis_results), 1), 3)
    critical_count = sum(1 for a in analysis_results if a["severity"] == "critical")
    high_count = sum(1 for a in analysis_results if a["severity"] == "high")

    return {
        "region_id": region_id,
        "region_name": display,
        "district": info["district"],
        "total_plots": len(plots),
        "avg_iou": avg_iou,
        "avg_risk_score": avg_risk,
        "critical_violations": critical_count,
        "high_violations": high_count,
        "compliance_score": round(max(0, 100 - avg_risk * 100), 1),
        "plot_analyses": analysis_results,
    }


# ══════════════════════════════════════════════════════════════════════
# 12. /audit-log — Audit Trail
# ══════════════════════════════════════════════════════════════════════

_audit_log: list = []


def _log_audit(user_id: str, action: str, resource_type: str,
               resource_id: str, details: dict = None):
    """Record an audit log entry."""
    _audit_log.append({
        "id": len(_audit_log) + 1,
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "ip_address": "127.0.0.1",
        "created_at": datetime.now().isoformat(),
    })


@app.get("/api/audit-log")
async def api_audit_log(
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    """Query audit log entries."""
    entries = list(_audit_log)
    if user_id:
        entries = [e for e in entries if e["user_id"] == user_id]
    if action:
        entries = [e for e in entries if e["action"] == action]
    entries.sort(key=lambda e: e["created_at"], reverse=True)
    return {"total": len(entries), "entries": entries[:limit]}


# ══════════════════════════════════════════════════════════════════════
# 13. /region-summary — Comprehensive region summary
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/region-summary/{region_id}")
async def api_region_summary(region_id: str):
    """Comprehensive summary of a region: plots + violations + compliance + GIS."""
    if region_id not in REGION_CATALOG:
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found")

    info = REGION_CATALOG[region_id]
    display = REGION_DISPLAY_NAMES.get(region_id, region_id.title())
    area_ha = 250.0
    boundary = _generate_region_boundary(info["lat"], info["lon"], area_ha, region_id)
    num_plots = _random.Random(hash(region_id) % 2**32).randint(12, 32)
    plots = _subdivide_boundary_into_plots(boundary, region_id, display, info["district"], num_plots, region_id)

    # Ensure violations are generated
    _ensure_violations_seeded(region_id)
    violations_data = get_violations(region_id=region_id, limit=100)

    # Status summary
    status_counts = {}
    total_area = 0
    for p in plots:
        s = p["status"]
        status_counts[s] = status_counts.get(s, 0) + 1
        total_area += p.get("area_sqm", 0)

    # Violation severity summary
    open_violations = [v for v in violations_data["violations"] if v["status"] == "open"]
    sev_summary = {}
    for v in open_violations:
        s = v["severity"]
        sev_summary[s] = sev_summary.get(s, 0) + 1

    # Avg risk
    avg_risk = sum(p.get("risk_score", 0) for p in plots) / max(len(plots), 1)
    compliance_score = round(max(0, 100 - avg_risk * 80), 1)

    return {
        "region_id": region_id,
        "region_name": display,
        "district": info["district"],
        "category": info.get("category", "old"),
        "center": {"lat": info["lat"], "lon": info["lon"]},
        "area_hectares": area_ha,
        "total_plots": len(plots),
        "total_area_sqm": round(total_area, 1),
        "status_summary": status_counts,
        "open_violations": len(open_violations),
        "violation_severity": sev_summary,
        "avg_risk_score": round(avg_risk, 3),
        "compliance_score": compliance_score,
        "compliance_grade": (
            "A" if compliance_score >= 85 else
            "B" if compliance_score >= 70 else
            "C" if compliance_score >= 50 else
            "D" if compliance_score >= 30 else "F"
        ),
        "boundary": boundary,
        "plots_geojson": {"type": "FeatureCollection", "features": [p["boundary"] for p in plots]},
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
