"""
ILMCS — Change Detection Service
Real pixel-based analysis comparing current vs historical satellite imagery.

Pipeline:
  1. Fetch Wayback tiles for both dates → compose into images
  2. Pixel-wise difference → binary change mask
  3. Pseudo-NDVI from RGB (Green as NIR proxy)
  4. Built-up area estimation from brightness/blue-ratio
  5. Change mask → contiguous regions → GeoJSON polygons
"""

import math
import time
import logging
import base64
import io
import httpx
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from scipy import ndimage

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════
# Wayback release catalog (same as main.py — import if available)
# ══════════════════════════════════════════════════════════════════════
_WAYBACK_RELEASES = [
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


def _find_closest_release(date_str: str) -> tuple:
    """Find the Wayback release closest to the requested date."""
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        target = datetime(2020, 1, 1)

    best = _WAYBACK_RELEASES[0]
    best_diff = abs((datetime.strptime(best[0], "%Y-%m-%d") - target).days)
    for rel_date, rel_m in _WAYBACK_RELEASES:
        diff = abs((datetime.strptime(rel_date, "%Y-%m-%d") - target).days)
        if diff < best_diff:
            best = (rel_date, rel_m)
            best_diff = diff
    return best


def _latlon_to_tile(lat: float, lon: float, zoom: int) -> tuple:
    """Convert lat/lon to tile x, y at given zoom level."""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(math.radians(lat)) + 1.0 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


def _tile_to_latlon(x: int, y: int, zoom: int) -> tuple:
    """Convert tile x, y back to lat/lon (top-left corner of tile)."""
    n = 2 ** zoom
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


# ══════════════════════════════════════════════════════════════════════
# Tile fetching — download & compose
# ══════════════════════════════════════════════════════════════════════

async def _fetch_tiles_as_image(
    lat: float, lon: float, bbox_km: float,
    rel_m: int, size: int = 512,
) -> Optional[np.ndarray]:
    """
    Fetch Wayback tiles for a specific release and compose into a numpy array.
    Returns RGB numpy array of shape (size, size, 3) or None on failure.
    """
    if not PIL_AVAILABLE:
        return None

    # Build bbox
    dlat = bbox_km / 111.32
    dlon = bbox_km / (111.32 * math.cos(math.radians(lat)))
    min_lat = lat - dlat
    max_lat = lat + dlat
    min_lon = lon - dlon
    max_lon = lon + dlon

    # Zoom level
    if bbox_km <= 1:
        zoom = 15
    elif bbox_km <= 3:
        zoom = 14
    elif bbox_km <= 6:
        zoom = 13
    elif bbox_km <= 12:
        zoom = 12
    else:
        zoom = 11

    # Tile range
    x_min, y_max = _latlon_to_tile(min_lat, min_lon, zoom)
    x_max, y_min = _latlon_to_tile(max_lat, max_lon, zoom)

    if x_min == x_max:
        x_max += 1
    if y_min == y_max:
        y_max += 1

    x_max = min(x_max, x_min + 5)
    y_max = min(y_max, y_min + 5)

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


# ══════════════════════════════════════════════════════════════════════
# Real analysis functions
# ══════════════════════════════════════════════════════════════════════

def compute_image_difference(
    img_before: np.ndarray,
    img_after: np.ndarray,
    threshold: float = 25.0,
) -> Tuple[np.ndarray, float]:
    """
    Real pixel-wise absolute difference between two satellite images.
    Returns binary change mask and changed pixel percentage.
    """
    # Convert to float and compute per-channel absolute difference
    diff = np.abs(img_after.astype(np.float32) - img_before.astype(np.float32))

    # Average across RGB channels
    if diff.ndim == 3:
        diff_gray = np.mean(diff, axis=2)
    else:
        diff_gray = diff

    # Threshold to get binary change mask
    raw_mask = (diff_gray > threshold).astype(np.uint8)

    # Morphological cleanup: remove small noise, fill small holes
    # Open (erode then dilate) to remove salt noise
    struct = np.ones((3, 3), dtype=np.uint8)
    mask = ndimage.binary_opening(raw_mask, structure=struct, iterations=2).astype(np.uint8)
    # Close (dilate then erode) to fill small holes
    mask = ndimage.binary_closing(mask, structure=struct, iterations=1).astype(np.uint8)

    # Calculate percentage
    pct = float(mask.sum()) / mask.size * 100
    return mask, round(pct, 2), diff_gray


def compute_pseudo_ndvi(img: np.ndarray) -> np.ndarray:
    """
    Compute pseudo-NDVI from RGB image.
    Uses Green channel as NIR proxy: pseudo_NDVI = (G - R) / (G + R)
    This approximates vegetation density from standard RGB imagery.
    """
    red = img[:, :, 0].astype(np.float32)
    green = img[:, :, 1].astype(np.float32)

    denom = green + red
    ndvi = np.where(denom > 0, (green - red) / denom, 0.0)
    return np.clip(ndvi, -1.0, 1.0)


def compute_built_up_ratio(img: np.ndarray) -> float:
    """
    Estimate built-up area percentage from RGB image.
    Built-up areas are typically:
    - Higher brightness (mean RGB > threshold)
    - Lower vegetation (low Green-Red difference)
    - More gray/concrete (low saturation)
    """
    r = img[:, :, 0].astype(np.float32)
    g = img[:, :, 1].astype(np.float32)
    b = img[:, :, 2].astype(np.float32)

    brightness = (r + g + b) / 3.0

    # Saturation approximation (low saturation = gray = built-up)
    max_ch = np.maximum(np.maximum(r, g), b)
    min_ch = np.minimum(np.minimum(r, g), b)
    sat = np.where(max_ch > 0, (max_ch - min_ch) / max_ch, 0.0)

    # Built-up: bright, low saturation, not very green relative to red
    is_bright = brightness > 80
    is_low_sat = sat < 0.35
    is_not_vegetation = (g - r) < 15

    built_up_mask = is_bright & is_low_sat & is_not_vegetation
    pct = float(built_up_mask.sum()) / built_up_mask.size * 100
    return round(pct, 1)


def _mask_to_geojson(
    mask: np.ndarray,
    lat: float, lon: float, bbox_km: float,
    min_region_size: int = 50,
    max_features: int = 20,
) -> Dict:
    """
    Convert a binary change mask to GeoJSON polygons.
    Labels connected components and converts each to a bounding polygon.
    """
    # Label connected components
    labeled, num_features = ndimage.label(mask)
    h, w = mask.shape

    # Geo bounds
    dlat = bbox_km / 111.32
    dlon = bbox_km / (111.32 * math.cos(math.radians(lat)))
    min_lat_bb = lat - dlat
    max_lat_bb = lat + dlat
    min_lon_bb = lon - dlon
    max_lon_bb = lon + dlon
    lat_range = max_lat_bb - min_lat_bb
    lon_range = max_lon_bb - min_lon_bb

    features = []
    regions = ndimage.find_objects(labeled)

    # Sort regions by size (largest first)
    region_sizes = []
    for i, slc in enumerate(regions):
        if slc is None:
            continue
        region_mask = (labeled[slc] == (i + 1))
        region_sizes.append((i, slc, int(region_mask.sum())))

    region_sizes.sort(key=lambda x: x[2], reverse=True)

    for idx, (i, slc, size) in enumerate(region_sizes):
        if size < min_region_size:
            continue
        if idx >= max_features:
            break

        # Get bounding box of this region in pixel coords
        row_slice, col_slice = slc
        r_min, r_max = row_slice.start, row_slice.stop
        c_min, c_max = col_slice.start, col_slice.stop

        # Add small padding
        pad = 2
        r_min = max(0, r_min - pad)
        r_max = min(h, r_max + pad)
        c_min = max(0, c_min - pad)
        c_max = min(w, c_max + pad)

        # Convert pixel coords to geo coords
        lon1 = min_lon_bb + (c_min / w) * lon_range
        lon2 = min_lon_bb + (c_max / w) * lon_range
        lat1 = max_lat_bb - (r_max / h) * lat_range  # Flip Y axis
        lat2 = max_lat_bb - (r_min / h) * lat_range

        # Create polygon (rectangle for each change region)
        coords = [
            [round(lon1, 6), round(lat1, 6)],
            [round(lon2, 6), round(lat1, 6)],
            [round(lon2, 6), round(lat2, 6)],
            [round(lon1, 6), round(lat2, 6)],
            [round(lon1, 6), round(lat1, 6)],  # Close ring
        ]

        # Estimate area in sq meters
        lat_m = abs(lat2 - lat1) * 111320
        lon_m = abs(lon2 - lon1) * 111320 * math.cos(math.radians(lat))
        area_sqm = round(lat_m * lon_m, 0)

        # Classify change type based on pixel analysis of the region
        features.append({
            "type": "Feature",
            "properties": {
                "change_type": "detected_change",
                "pixel_count": size,
                "area_sqm": area_sqm,
                "confidence": round(min(0.95, 0.5 + size / 2000), 2),
            },
            "geometry": {"type": "Polygon", "coordinates": [coords]},
        })

    return {"type": "FeatureCollection", "features": features}


def _classify_change_regions(
    change_mask: np.ndarray,
    img_before: np.ndarray,
    img_after: np.ndarray,
    labeled: np.ndarray,
    regions: list,
) -> Dict[str, int]:
    """
    Classify each change region by comparing before/after pixel properties.
    Returns type counts.
    """
    type_counts = {
        "new_construction": 0,
        "vegetation_loss": 0,
        "land_clearing": 0,
        "vegetation_growth": 0,
        "other_change": 0,
    }

    ndvi_before = compute_pseudo_ndvi(img_before)
    ndvi_after = compute_pseudo_ndvi(img_after)

    for i, slc in enumerate(regions):
        if slc is None:
            continue
        region_mask = (labeled[slc] == (i + 1))
        if region_mask.sum() < 30:
            continue

        # Average NDVI change in this region
        ndvi_diff = ndvi_after[slc][region_mask].mean() - ndvi_before[slc][region_mask].mean()

        # Average brightness change
        bright_before = img_before[slc][region_mask].mean()
        bright_after = img_after[slc][region_mask].mean()

        if ndvi_diff < -0.05 and bright_after > bright_before:
            type_counts["new_construction"] += 1
        elif ndvi_diff < -0.03:
            type_counts["vegetation_loss"] += 1
        elif ndvi_diff > 0.05:
            type_counts["vegetation_growth"] += 1
        elif bright_after > bright_before + 20:
            type_counts["land_clearing"] += 1
        else:
            type_counts["other_change"] += 1

    return type_counts


def _generate_change_overlay(
    diff_gray: np.ndarray,
    change_mask: np.ndarray,
) -> str:
    """
    Generate a real change overlay image from the actual difference data.
    Returns base64-encoded PNG with heat-mapped change intensity.
    """
    if not PIL_AVAILABLE:
        return ""

    h, w = diff_gray.shape

    # Normalize difference to 0-255
    diff_norm = np.clip(diff_gray / diff_gray.max() * 255 if diff_gray.max() > 0 else diff_gray, 0, 255).astype(np.uint8)

    # Create RGBA overlay: red channel = diff intensity, alpha = change mask
    overlay = np.zeros((h, w, 4), dtype=np.uint8)
    overlay[:, :, 0] = diff_norm  # Red = change intensity
    overlay[:, :, 1] = np.where(change_mask > 0, 40, 0)  # Slight green tint
    overlay[:, :, 2] = 0
    overlay[:, :, 3] = np.where(change_mask > 0, np.clip(diff_norm * 0.7, 40, 180).astype(np.uint8), 0)

    img = Image.fromarray(overlay, "RGBA")

    # Slight blur for smoother visualization
    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ══════════════════════════════════════════════════════════════════════
# Main change detection pipeline
# ══════════════════════════════════════════════════════════════════════

async def detect_changes(
    lat: float,
    lon: float,
    date_before: str,
    date_after: str,
    bbox_km: float = 2.0,
    methods: Optional[List[str]] = None,
) -> Dict:
    """
    Real change detection pipeline.
    Downloads satellite tiles for both dates and performs actual pixel analysis.
    """
    if methods is None:
        methods = ["image_diff", "ndvi", "built_up"]

    start = time.time()

    # Find closest Wayback releases for both dates
    rel_before_date, rel_before_m = _find_closest_release(date_before)
    rel_after_date, rel_after_m = _find_closest_release(date_after)

    logger.info(
        f"Real change detection: {date_before}→{date_after} | "
        f"Releases: {rel_before_date}(M={rel_before_m}) vs {rel_after_date}(M={rel_after_m})"
    )

    # Download tiles for both dates
    analysis_size = 512  # Resolution for analysis
    img_before = await _fetch_tiles_as_image(lat, lon, bbox_km, rel_before_m, size=analysis_size)
    img_after = await _fetch_tiles_as_image(lat, lon, bbox_km, rel_after_m, size=analysis_size)

    if img_before is None or img_after is None:
        logger.error("Failed to fetch tiles for change detection")
        return {
            "error": "Failed to download satellite imagery for analysis",
            "center": {"lat": lat, "lon": lon},
            "date_before": date_before,
            "date_after": date_after,
            "changed_area_pct": 0,
            "change_percentage": 0,
            "methods_applied": methods,
            "processing_time_ms": int((time.time() - start) * 1000),
        }

    result = {
        "center": {"lat": lat, "lon": lon},
        "date_before": date_before,
        "date_after": date_after,
        "release_before": rel_before_date,
        "release_after": rel_after_date,
        "analysis_resolution": f"{analysis_size}x{analysis_size}",
        "methods_applied": methods,
        "is_real_analysis": True,
        "processing_time_ms": 0,
    }

    # ── 1. Image Difference (pixel-wise) ───────────────────────────
    change_mask, change_pct, diff_gray = compute_image_difference(
        img_before, img_after, threshold=25.0
    )

    result["changed_area_pct"] = change_pct
    result["change_percentage"] = change_pct  # alias

    # Area calculation
    area_sqkm = (bbox_km * 2) ** 2
    changed_sqm = round(area_sqkm * 1e6 * change_pct / 100, 0)
    result["changed_area_sqm"] = changed_sqm

    # ── 2. NDVI Analysis ──────────────────────────────────────────
    if "ndvi" in methods:
        ndvi_before = compute_pseudo_ndvi(img_before)
        ndvi_after = compute_pseudo_ndvi(img_after)

        result["ndvi_before"] = round(float(ndvi_before.mean()), 4)
        result["ndvi_after"] = round(float(ndvi_after.mean()), 4)
        result["ndvi_change"] = round(float(ndvi_after.mean() - ndvi_before.mean()), 4)
        result["ndvi_std_before"] = round(float(ndvi_before.std()), 4)
        result["ndvi_std_after"] = round(float(ndvi_after.std()), 4)

    # ── 3. Built-up Area Analysis ─────────────────────────────────
    if "built_up" in methods:
        bu_before = compute_built_up_ratio(img_before)
        bu_after = compute_built_up_ratio(img_after)

        result["built_up_before_pct"] = bu_before
        result["built_up_after_pct"] = bu_after

    # ── 4. Change region classification ───────────────────────────
    labeled_mask, num_regions = ndimage.label(change_mask)
    regions = ndimage.find_objects(labeled_mask)

    type_counts = _classify_change_regions(
        change_mask, img_before, img_after, labeled_mask, regions
    )
    result["new_construction_count"] = type_counts["new_construction"]
    result["vegetation_loss_count"] = type_counts["vegetation_loss"]
    result["land_clearing_count"] = type_counts["land_clearing"]
    result["vegetation_growth_count"] = type_counts["vegetation_growth"]
    result["total_change_regions"] = sum(type_counts.values())
    result["change_type_counts"] = type_counts

    # ── 5. Generate change GeoJSON from real mask ─────────────────
    change_geojson = _mask_to_geojson(change_mask, lat, lon, bbox_km)
    result["change_geojson"] = change_geojson
    result["change_overlay_geojson"] = change_geojson

    # Update feature properties with classification
    for feat in change_geojson["features"]:
        # Re-classify individual features based on their location
        coords = feat["geometry"]["coordinates"][0]
        center_lon = (coords[0][0] + coords[2][0]) / 2
        center_lat = (coords[0][1] + coords[2][1]) / 2

        # Map pixel location in image
        dlat = bbox_km / 111.32
        dlon = bbox_km / (111.32 * math.cos(math.radians(lat)))
        px = int(((center_lon - (lon - dlon)) / (2 * dlon)) * analysis_size)
        py = int(((lat + dlat - center_lat) / (2 * dlat)) * analysis_size)
        px = max(0, min(px, analysis_size - 1))
        py = max(0, min(py, analysis_size - 1))

        # Sample 5x5 neighborhood
        r = 5
        py_min, py_max = max(0, py - r), min(analysis_size, py + r)
        px_min, px_max = max(0, px - r), min(analysis_size, px + r)

        ndvi_b = compute_pseudo_ndvi(img_before[py_min:py_max, px_min:px_max])
        ndvi_a = compute_pseudo_ndvi(img_after[py_min:py_max, px_min:px_max])
        ndvi_diff = float(ndvi_a.mean() - ndvi_b.mean()) if ndvi_a.size > 0 else 0

        bright_b = float(img_before[py_min:py_max, px_min:px_max].mean())
        bright_a = float(img_after[py_min:py_max, px_min:px_max].mean())

        if ndvi_diff < -0.04 and bright_a > bright_b:
            feat["properties"]["change_type"] = "new_construction"
        elif ndvi_diff < -0.02:
            feat["properties"]["change_type"] = "vegetation_loss"
        elif ndvi_diff > 0.04:
            feat["properties"]["change_type"] = "vegetation_growth"
        elif bright_a > bright_b + 15:
            feat["properties"]["change_type"] = "land_clearing"
        else:
            feat["properties"]["change_type"] = "detected_change"

    # ── 6. Generate real overlay image ────────────────────────────
    result["change_overlay_b64"] = _generate_change_overlay(diff_gray, change_mask)

    result["processing_time_ms"] = int((time.time() - start) * 1000)
    logger.info(
        f"Change detection complete: {change_pct}% changed, "
        f"{len(change_geojson['features'])} regions, "
        f"{result['processing_time_ms']}ms"
    )
    return result
