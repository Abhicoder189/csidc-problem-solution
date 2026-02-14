"""
ILMCS — Plot Historical Change Detection Service
Multi-temporal analysis for individual plots across historical satellite imagery.

Features:
  - Timeline of satellite imagery for a specific plot
  - Automated change point detection
  - Plot-wise NDVI, built-up area, and vegetation trends
  - GeoJSON boundary-based cropping
  - Time-series analytics
"""

import math
import logging
import asyncio
import base64
import io
import httpx
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from shapely.geometry import shape, Point, Polygon
from scipy import ndimage
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# Wayback release catalog
WAYBACK_RELEASES = [
    ("2026-01-29", 22252), ("2025-12-18", 13192), ("2025-11-20", 51127),
    ("2025-06-26", 48925), ("2025-01-30", 36557),
    ("2024-12-12", 16453), ("2024-06-27", 39767), ("2024-02-08", 37965),
    ("2023-12-07", 56102), ("2023-06-29", 47963), ("2023-01-11", 11475),
    ("2022-12-14", 45134), ("2022-06-08", 44710), ("2022-01-12", 42663),
    ("2021-12-21", 26120), ("2021-06-30", 13534), ("2021-01-13", 1049),
    ("2020-12-16", 29260), ("2020-06-10", 11135), ("2020-01-08", 23001),
    ("2019-12-12", 4756),  ("2019-06-26", 645),   ("2019-01-09", 6036),
    ("2018-12-14", 23448), ("2018-06-06", 8249),   ("2018-01-18", 13045),
    ("2017-11-16", 25521), ("2017-05-31", 14342),  ("2017-01-11", 577),
    ("2016-12-07", 6678),  ("2016-06-13", 11509),  ("2016-03-16", 19085),
    ("2014-02-20", 10768),
]


def _latlon_to_tile(lat: float, lon: float, zoom: int) -> tuple:
    """Convert lat/lon to tile x, y at given zoom level."""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(math.radians(lat)) + 1.0 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


def compute_bbox_from_geojson(geojson: dict) -> Tuple[float, float, float, float]:
    """Extract bounding box from GeoJSON geometry: (min_lat, max_lat, min_lon, max_lon)."""
    geom = shape(geojson)
    bounds = geom.bounds  # (minx, miny, maxx, maxy) 
    return bounds[1], bounds[3], bounds[0], bounds[2]  # min_lat, max_lat, min_lon, max_lon


def compute_plot_centroid(geojson: dict) -> Tuple[float, float]:
    """Compute centroid (lat, lon) from GeoJSON geometry."""
    geom = shape(geojson)
    centroid = geom.centroid
    return centroid.y, centroid.x  # lat, lon


async def fetch_plot_image_for_date(
    plot_geojson: dict,
    date: str,
    size: int = 512,
) -> Optional[dict]:
    """
    Fetch satellite imagery for a specific plot and date.
    Returns dict with image data, NDVI, built-up metrics.
    """
    try:
        # Find closest Wayback release
        target_dt = datetime.strptime(date, "%Y-%m-%d")
        best_release = WAYBACK_RELEASES[0]
        best_diff = abs((datetime.strptime(best_release[0], "%Y-%m-%d") - target_dt).days)
        
        for rel_date, rel_m in WAYBACK_RELEASES:
            diff = abs((datetime.strptime(rel_date, "%Y-%m-%d") - target_dt).days)
            if diff < best_diff:
                best_release = (rel_date, rel_m)
                best_diff = diff
        
        rel_date, rel_m = best_release
        
        # Compute bbox and centroid
        min_lat, max_lat, min_lon, max_lon = compute_bbox_from_geojson(plot_geojson)
        center_lat, center_lon = compute_plot_centroid(plot_geojson)
        
        # Calculate bbox size in km
        lat_diff = max_lat - min_lat
        lon_diff = max_lon - min_lon
        bbox_km = max(lat_diff * 111.32, lon_diff * 111.32 * math.cos(math.radians(center_lat))) + 0.5
        
        # Fetch tiles
        img_array = await _fetch_tiles_for_bbox(
            min_lat, max_lat, min_lon, max_lon, rel_m, size
        )
        
        if img_array is None:
            return None
        
        # Create mask for plot boundary
        mask = _create_plot_mask(plot_geojson, min_lat, max_lat, min_lon, max_lon, size)
        
        # Apply mask to image
        masked_img = img_array.copy()
        if mask is not None:
            for i in range(3):
                masked_img[:, :, i] = masked_img[:, :, i] * mask
        
        # Compute metrics
        ndvi = _compute_pseudo_ndvi(masked_img, mask)
        built_up_pct = _compute_built_up_percentage(masked_img, mask)
        vegetation_pct = _compute_vegetation_percentage(masked_img, mask)
        
        # Convert to base64
        img_pil = Image.fromarray(masked_img)
        buffer = io.BytesIO()
        img_pil.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "date": date,
            "actual_date": rel_date,
            "days_diff": best_diff,
            "image_b64": img_b64,
            "ndvi": round(ndvi, 3),
            "built_up_percentage": round(built_up_pct, 2),
            "vegetation_percentage": round(vegetation_pct, 2),
            "image_url": f"data:image/png;base64,{img_b64}",
        }
    
    except Exception as e:
        logger.error(f"Error fetching plot image for {date}: {e}")
        return None


async def _fetch_tiles_for_bbox(
    min_lat: float, max_lat: float, min_lon: float, max_lon: float,
    rel_m: int, size: int = 512
) -> Optional[np.ndarray]:
    """Fetch and composite tiles for bounding box."""
    # Determine zoom level
    lat_diff = max_lat - min_lat
    lon_diff = max_lon - min_lon
    avg_lat = (min_lat + max_lat) / 2
    bbox_km = max(lat_diff * 111.32, lon_diff * 111.32 * math.cos(math.radians(avg_lat)))
    
    if bbox_km <= 0.5:
        zoom = 17
    elif bbox_km <= 1:
        zoom = 16
    elif bbox_km <= 2:
        zoom = 15
    elif bbox_km <= 4:
        zoom = 14
    else:
        zoom = 13
    
    # Get tile range
    x_min, y_max = _latlon_to_tile(min_lat, min_lon, zoom)
    x_max, y_min = _latlon_to_tile(max_lat, max_lon, zoom)
    
    if x_min == x_max:
        x_max += 1
    if y_min == y_max:
        y_max += 1
    
    x_max = min(x_max, x_min + 4)
    y_max = min(y_max, y_min + 4)
    
    n_cols = x_max - x_min + 1
    n_rows = y_max - y_min + 1
    tile_size = 256
    
    composed = Image.new("RGB", (n_cols * tile_size, n_rows * tile_size), (20, 20, 30))
    tiles_ok = 0
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for row in range(n_rows):
            for col in range(n_cols):
                tx = x_min + col
                ty = y_min + row
                tile_url = (
                    f"https://wayback.maptiles.arcgis.com/arcgis/rest/services/"
                    f"World_Imagery/MapServer/tile/{rel_m}/{zoom}/{ty}/{tx}"
                )
                try:
                    resp = await client.get(tile_url)
                    if resp.status_code == 200 and len(resp.content) > 500:
                        tile_img = Image.open(io.BytesIO(resp.content))
                        if tile_img.mode != "RGB":
                            tile_img = tile_img.convert("RGB")
                        composed.paste(tile_img, (col * tile_size, row * tile_size))
                        tiles_ok += 1
                except Exception as e:
                    logger.warning(f"Tile {zoom}/{ty}/{tx} failed: {e}")
    
    if tiles_ok == 0:
        return None
    
    composed = composed.resize((size, size), Image.LANCZOS)
    return np.array(composed, dtype=np.uint8)


def _create_plot_mask(
    geojson: dict, min_lat: float, max_lat: float, min_lon: float, max_lon: float, size: int
) -> Optional[np.ndarray]:
    """Create binary mask for plot boundary."""
    try:
        geom = shape(geojson)
        img = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(img)
        
        if geojson["type"] == "Polygon":
            coords = geojson["coordinates"][0]
        elif geojson["type"] == "MultiPolygon":
            # Use first polygon
            coords = geojson["coordinates"][0][0]
        else:
            return None
        
        # Convert lat/lon to pixel coordinates
        pixel_coords = []
        for lon, lat in coords:
            x = int((lon - min_lon) / (max_lon - min_lon) * size)
            y = int((max_lat - lat) / (max_lat - min_lat) * size)
            pixel_coords.append((x, y))
        
        draw.polygon(pixel_coords, fill=255)
        mask = np.array(img, dtype=np.float32) / 255.0
        return mask
    
    except Exception as e:
        logger.error(f"Error creating plot mask: {e}")
        return None


def _compute_pseudo_ndvi(img: np.ndarray, mask: Optional[np.ndarray] = None) -> float:
    """Compute pseudo-NDVI using Green as NIR proxy: (G - R) / (G + R)."""
    r = img[:, :, 0].astype(np.float32)
    g = img[:, :, 1].astype(np.float32)
    
    if mask is not None:
        r = r * mask
        g = g * mask
        valid = mask > 0.5
    else:
        valid = np.ones(r.shape, dtype=bool)
    
    denom = g + r + 1e-6
    ndvi = (g - r) / denom
    
    if valid.sum() > 0:
        return float(ndvi[valid].mean())
    return 0.0


def _compute_built_up_percentage(img: np.ndarray, mask: Optional[np.ndarray] = None) -> float:
    """Estimate built-up area based on brightness and blue ratio."""
    gray = np.mean(img, axis=2).astype(np.float32)
    blue_ratio = img[:, :, 2].astype(np.float32) / (gray + 1e-6)
    
    # Built up areas: bright (>150) and high blue ratio (>0.35)
    built_up = (gray > 150) & (blue_ratio > 0.35)
    
    if mask is not None:
        valid = mask > 0.5
        built_up = built_up & valid
        total = valid.sum()
    else:
        total = built_up.size
    
    if total > 0:
        return float(built_up.sum()) / total * 100
    return 0.0


def _compute_vegetation_percentage(img: np.ndarray, mask: Optional[np.ndarray] = None) -> float:
    """Estimate vegetation based on green dominance."""
    r = img[:, :, 0].astype(np.float32)
    g = img[:, :, 1].astype(np.float32)
    b = img[:, :, 2].astype(np.float32)
    
    # Vegetation: green dominant and not too bright
    vegetation = (g > r) & (g > b) & (g > 60) & (g < 200)
    
    if mask is not None:
        valid = mask > 0.5
        vegetation = vegetation & valid
        total = valid.sum()
    else:
        total = vegetation.size
    
    if total > 0:
        return float(vegetation.sum()) / total * 100
    return 0.0


async def analyze_plot_timeline(
    plot_geojson: dict,
    start_date: str,
    end_date: str,
    num_snapshots: int = 6,
) -> dict:
    """
    Analyze plot changes across timeline with multiple snapshots.
    Returns time-series data with change detection.
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Generate evenly spaced dates
    total_days = (end_dt - start_dt).days
    interval = total_days // (num_snapshots - 1) if num_snapshots > 1 else 0
    
    dates = []
    for i in range(num_snapshots):
        date = start_dt + timedelta(days=i * interval)
        if date <= end_dt:
            dates.append(date.strftime("%Y-%m-%d"))
    
    # Ensure end date is included
    if dates[-1] != end_date:
        dates[-1] = end_date
    
    # Fetch images for each date
    tasks = [fetch_plot_image_for_date(plot_geojson, date) for date in dates]
    results = await asyncio.gather(*tasks)
    
    # Filter out failed fetches
    snapshots = [r for r in results if r is not None]
    
    if len(snapshots) < 2:
        return {
            "success": False,
            "error": "Insufficient imagery available",
            "snapshots": []
        }
    
    # Detect change points
    change_points = []
    for i in range(1, len(snapshots)):
        prev = snapshots[i - 1]
        curr = snapshots[i]
        
        ndvi_change = abs(curr["ndvi"] - prev["ndvi"])
        built_up_change = abs(curr["built_up_percentage"] - prev["built_up_percentage"])
        
        if ndvi_change > 0.1 or built_up_change > 10:
            change_points.append({
                "from_date": prev["actual_date"],
                "to_date": curr["actual_date"],
                "ndvi_change": round(curr["ndvi"] - prev["ndvi"], 3),
                "built_up_change": round(curr["built_up_percentage"] - prev["built_up_percentage"], 2),
                "significance": "high" if (ndvi_change > 0.2 or built_up_change > 20) else "medium",
            })
    
    return {
        "success": True,
        "snapshots": snapshots,
        "change_points": change_points,
        "summary": {
            "total_snapshots": len(snapshots),
            "ndvi_trend": round(snapshots[-1]["ndvi"] - snapshots[0]["ndvi"], 3),
            "built_up_trend": round(snapshots[-1]["built_up_percentage"] - snapshots[0]["built_up_percentage"], 2),
            "vegetation_trend": round(snapshots[-1]["vegetation_percentage"] - snapshots[0]["vegetation_percentage"], 2),
        }
    }


def detect_plot_anomalies(snapshots: List[dict]) -> List[dict]:
    """Detect anomalies in time-series data."""
    if len(snapshots) < 3:
        return []
    
    anomalies = []
    ndvi_values = [s["ndvi"] for s in snapshots]
    built_up_values = [s["built_up_percentage"] for s in snapshots]
    
    # Compute moving averages
    ndvi_mean = np.mean(ndvi_values)
    ndvi_std = np.std(ndvi_values)
    built_up_mean = np.mean(built_up_values)
    built_up_std = np.std(built_up_values)
    
    for i, snapshot in enumerate(snapshots):
        ndvi_z = abs((snapshot["ndvi"] - ndvi_mean) / (ndvi_std + 1e-6))
        built_up_z = abs((snapshot["built_up_percentage"] - built_up_mean) / (built_up_std + 1e-6))
        
        if ndvi_z > 2.0 or built_up_z > 2.0:
            anomalies.append({
                "date": snapshot["actual_date"],
                "type": "ndvi_anomaly" if ndvi_z > built_up_z else "built_up_anomaly",
                "severity": "high" if max(ndvi_z, built_up_z) > 3.0 else "medium",
                "description": f"Significant deviation detected in {'vegetation' if ndvi_z > built_up_z else 'construction'} metrics",
            })
    
    return anomalies
