"""
ILMCS — GIS Engine
PostGIS spatial operations for boundary compliance analysis.
"""

from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from pyproj import Transformer
import numpy as np
from typing import Dict, Any, Optional


# UTM Zone 44N (Chhattisgarh) ↔ WGS84
_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
_to_wgs = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)

BUFFER_TOLERANCE_M = 5.0  # ½ Sentinel-2 pixel


def to_utm(geojson: dict) -> Any:
    """Convert GeoJSON geometry from WGS84 to UTM Zone 44N."""
    geom = shape(geojson)
    return _transform_geom(geom, _to_utm)


def to_wgs84(geom) -> dict:
    """Convert Shapely geometry back to WGS84 GeoJSON."""
    return mapping(_transform_geom(geom, _to_wgs))


def _transform_geom(geom, transformer):
    from shapely.ops import transform as shapely_transform
    return shapely_transform(transformer.transform, geom)


def compute_iou(allotted_geojson: dict, detected_geojson: dict) -> float:
    """
    Intersection-over-Union between allotted boundary and detected structure.
    Both inputs in EPSG:4326; computation in EPSG:32644 (metric).
    """
    allotted = to_utm(allotted_geojson)
    detected = to_utm(detected_geojson)

    intersection = allotted.intersection(detected).area
    union = allotted.union(detected).area

    if union == 0:
        return 0.0
    return round(intersection / union, 4)


def compute_area_deviation(allotted_geojson: dict, detected_geojson: dict) -> Dict[str, float]:
    """
    Compute area deviation between allotted and detected boundaries.
    Returns deviation ratio and areas in sqm.
    """
    allotted = to_utm(allotted_geojson)
    detected = to_utm(detected_geojson)

    allotted_area = allotted.area
    detected_area = detected.area
    deviation = abs(detected_area - allotted_area) / allotted_area if allotted_area > 0 else 0.0

    return {
        "allotted_area_sqm": round(allotted_area, 2),
        "detected_area_sqm": round(detected_area, 2),
        "deviation_ratio": round(deviation, 4),
        "deviation_sqm": round(abs(detected_area - allotted_area), 2),
    }


def extract_encroachment(
    allotted_geojson: dict,
    detected_geojson: dict,
    buffer_m: float = BUFFER_TOLERANCE_M,
) -> Optional[dict]:
    """
    Extract the encroachment polygon (detected area outside allotted boundary + buffer).
    Returns GeoJSON of encroachment in WGS84, or None if within tolerance.
    """
    allotted = to_utm(allotted_geojson)
    detected = to_utm(detected_geojson)

    buffered_allotted = allotted.buffer(buffer_m)
    encroachment = detected.difference(buffered_allotted)

    if encroachment.is_empty or encroachment.area < 1.0:  # < 1 m²
        return None

    return {
        "geometry": to_wgs84(encroachment),
        "area_sqm": round(encroachment.area, 2),
    }


def compute_risk_score(
    iou: float,
    area_deviation: float,
    encroachment_area: float,
    temporal_persistence: float = 0.0,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Weighted composite risk score [0, 1].
    Higher = more risk.
    """
    w = weights or {
        "iou_weight": 0.30,
        "area_deviation_weight": 0.25,
        "encroachment_weight": 0.25,
        "temporal_weight": 0.20,
    }

    iou_risk = max(0, 1 - iou)
    area_risk = min(area_deviation, 1.0)
    encroach_risk = min(encroachment_area / 500.0, 1.0)  # Normalize to 500 m²
    temporal_risk = min(temporal_persistence, 1.0)

    score = (
        w["iou_weight"] * iou_risk
        + w["area_deviation_weight"] * area_risk
        + w["encroachment_weight"] * encroach_risk
        + w["temporal_weight"] * temporal_risk
    )
    return round(min(score, 1.0), 4)


def severity_from_score(score: float) -> str:
    """Map risk score to severity label."""
    if score >= 0.8:
        return "CRITICAL"
    elif score >= 0.6:
        return "SEVERE"
    elif score >= 0.4:
        return "HIGH"
    elif score >= 0.2:
        return "MEDIUM"
    return "LOW"
