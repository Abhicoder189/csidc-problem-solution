"""
ILMCS — GIS Computation Engine
Production-grade spatial analysis: IoU, area deviation, encroachment polygons,
buffer tolerance, Hausdorff distance, risk scoring.
All computations use WGS84 EPSG:4326 coordinates.
"""

import math
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# ── Earth constants ───────────────────────────────────────────────
EARTH_RADIUS_M = 6_371_000
DEG_TO_RAD = math.pi / 180.0
M_PER_DEG_LAT = 111_320.0


def m_per_deg_lon(lat: float) -> float:
    """Meters per degree longitude at given latitude."""
    return 111_320.0 * math.cos(lat * DEG_TO_RAD)


# ══════════════════════════════════════════════════════════════════
# Polygon area (Shoelace formula on projected coordinates)
# ══════════════════════════════════════════════════════════════════

def polygon_area_sqm(coords: List[List[float]]) -> float:
    """
    Compute area in m² for a polygon in [lon, lat] pairs.
    Uses Shoelace formula with local Mercator projection.
    coords: list of [lon, lat] — the ring should be closed.
    """
    if len(coords) < 4:
        return 0.0

    # Project to local meters from centroid
    cx = sum(c[0] for c in coords[:-1]) / max(len(coords) - 1, 1)
    cy = sum(c[1] for c in coords[:-1]) / max(len(coords) - 1, 1)
    scale_x = m_per_deg_lon(cy)
    scale_y = M_PER_DEG_LAT

    projected = [(
        (c[0] - cx) * scale_x,
        (c[1] - cy) * scale_y
    ) for c in coords]

    # Shoelace
    n = len(projected) - 1  # last == first
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += projected[i][0] * projected[j][1]
        area -= projected[j][0] * projected[i][1]
    return abs(area) / 2.0


def polygon_centroid(coords: List[List[float]]) -> Tuple[float, float]:
    """Compute centroid of a polygon. Returns (lon, lat)."""
    n = len(coords) - 1 if coords[0] == coords[-1] else len(coords)
    cx = sum(c[0] for c in coords[:n]) / max(n, 1)
    cy = sum(c[1] for c in coords[:n]) / max(n, 1)
    return (cx, cy)


# ══════════════════════════════════════════════════════════════════
# IoU (Intersection over Union)
# ══════════════════════════════════════════════════════════════════

def compute_iou(area_allotted: float, area_detected: float,
                area_intersection: float) -> float:
    """
    IoU = |A ∩ B| / |A ∪ B|
        = intersection / (A + B - intersection)
    """
    union = area_allotted + area_detected - area_intersection
    if union <= 0:
        return 1.0 if area_allotted <= 0 and area_detected <= 0 else 0.0
    return round(area_intersection / union, 4)


def compute_iou_from_areas(allotted: float, detected: float) -> float:
    """Simplified IoU when exact intersection is not computed."""
    intersection = min(allotted, detected)
    union = max(allotted, detected)
    return round(intersection / union, 4) if union > 0 else 1.0


# ══════════════════════════════════════════════════════════════════
# Area Deviation
# ══════════════════════════════════════════════════════════════════

def compute_area_deviation(allotted_sqm: float, detected_sqm: float) -> float:
    """
    δ_area = ((detected - allotted) / allotted) × 100%
    Positive → over-utilization / encroachment
    Negative → under-utilization
    """
    if allotted_sqm <= 0:
        return 0.0
    return round((detected_sqm - allotted_sqm) / allotted_sqm * 100, 2)


# ══════════════════════════════════════════════════════════════════
# Buffer Tolerance
# ══════════════════════════════════════════════════════════════════

def buffer_polygon(coords: List[List[float]], buffer_m: float) -> List[List[float]]:
    """
    Apply a simple buffer to a polygon by expanding each vertex outward.
    buffer_m: buffer distance in meters (positive = expand, negative = shrink).
    """
    if len(coords) < 4:
        return coords

    centroid = polygon_centroid(coords)
    cx, cy = centroid
    scale_x = m_per_deg_lon(cy)
    scale_y = M_PER_DEG_LAT

    buffered = []
    for c in coords[:-1]:
        dx = (c[0] - cx) * scale_x
        dy = (c[1] - cy) * scale_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1e-9:
            buffered.append(list(c))
            continue
        factor = (dist + buffer_m) / dist
        new_lon = cx + (c[0] - cx) * factor
        new_lat = cy + (c[1] - cy) * factor
        buffered.append([round(new_lon, 6), round(new_lat, 6)])

    buffered.append(buffered[0])
    return buffered


# ══════════════════════════════════════════════════════════════════
# Point-in-Polygon (Ray casting)
# ══════════════════════════════════════════════════════════════════

def point_in_polygon(lon: float, lat: float, coords: List[List[float]]) -> bool:
    """Ray-casting algorithm for point-in-polygon test."""
    n = len(coords) - 1
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = coords[i]
        xj, yj = coords[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


# ══════════════════════════════════════════════════════════════════
# Hausdorff Distance (boundary shift detection)
# ══════════════════════════════════════════════════════════════════

def _point_distance_m(p1: List[float], p2: List[float]) -> float:
    """Approximate distance in meters between two [lon, lat] points."""
    lat_avg = (p1[1] + p2[1]) / 2.0
    dx = (p2[0] - p1[0]) * m_per_deg_lon(lat_avg)
    dy = (p2[1] - p1[1]) * M_PER_DEG_LAT
    return math.sqrt(dx * dx + dy * dy)


def _directed_hausdorff(coords_a: List[List[float]], coords_b: List[List[float]]) -> float:
    """sup_{a ∈ A} inf_{b ∈ B} d(a, b)"""
    max_dist = 0.0
    for pa in coords_a:
        min_dist = float('inf')
        for pb in coords_b:
            d = _point_distance_m(pa, pb)
            if d < min_dist:
                min_dist = d
        if min_dist > max_dist:
            max_dist = min_dist
    return max_dist


def hausdorff_distance(coords_a: List[List[float]], coords_b: List[List[float]]) -> float:
    """
    Hausdorff distance d_H(A, B) = max(sup_a inf_b d(a,b), sup_b inf_a d(a,b))
    Returns distance in meters.
    """
    d1 = _directed_hausdorff(coords_a, coords_b)
    d2 = _directed_hausdorff(coords_b, coords_a)
    return round(max(d1, d2), 2)


# ══════════════════════════════════════════════════════════════════
# Polygon Intersection (Sutherland-Hodgman)
# ══════════════════════════════════════════════════════════════════

def _line_intersection(p1, p2, p3, p4):
    """Find intersection point of line p1-p2 and line p3-p4."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-12:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    ix = x1 + t * (x2 - x1)
    iy = y1 + t * (y2 - y1)
    return (ix, iy)


def _is_inside(point, edge_start, edge_end):
    """Check if point is on the left side of edge."""
    return ((edge_end[0] - edge_start[0]) * (point[1] - edge_start[1]) -
            (edge_end[1] - edge_start[1]) * (point[0] - edge_start[0])) >= 0


def polygon_intersection(subject: List[List[float]], clip: List[List[float]]) -> List[List[float]]:
    """
    Sutherland-Hodgman polygon clipping algorithm.
    Returns intersection polygon as list of [lon, lat].
    Both inputs should be closed rings (first == last).
    """
    output = [tuple(p) for p in subject[:-1]]
    clip_edges = [(tuple(clip[i]), tuple(clip[i + 1])) for i in range(len(clip) - 1)]

    for edge_start, edge_end in clip_edges:
        if not output:
            break
        input_list = output
        output = []
        for i in range(len(input_list)):
            current = input_list[i]
            prev = input_list[i - 1]

            if _is_inside(current, edge_start, edge_end):
                if not _is_inside(prev, edge_start, edge_end):
                    intersection = _line_intersection(prev, current, edge_start, edge_end)
                    if intersection:
                        output.append(intersection)
                output.append(current)
            elif _is_inside(prev, edge_start, edge_end):
                intersection = _line_intersection(prev, current, edge_start, edge_end)
                if intersection:
                    output.append(intersection)

    if output:
        result = [[round(p[0], 6), round(p[1], 6)] for p in output]
        result.append(result[0])
        return result
    return []


def polygon_difference(subject: List[List[float]], clip: List[List[float]]) -> List[List[float]]:
    """
    Approximate polygon difference: subject \ clip.
    Returns the encroachment polygon (parts of subject outside clip).
    For production, use Shapely or PostGIS ST_Difference.
    """
    # Simplified: return subject boundary adjusted
    inter = polygon_intersection(subject, clip)
    if not inter or len(inter) < 4:
        return subject  # No intersection = all encroachment
    inter_area = polygon_area_sqm(inter)
    subj_area = polygon_area_sqm(subject)
    if inter_area >= subj_area * 0.95:
        return []  # Almost fully contained
    return subject  # Return full subject as approximation


# ══════════════════════════════════════════════════════════════════
# Composite Risk Score
# ══════════════════════════════════════════════════════════════════

SEVERITY_WEIGHTS = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.2}


def compute_risk_score(
    severity: str,
    area_deviation_pct: float,
    confidence: float,
    iou: float,
    payment_default: bool = False,
    temporal_persistence: int = 1
) -> float:
    """
    R = w₁·S_severity + w₂·S_deviation + w₃·S_confidence + w₄·S_iou_departure
        + bonus for payment default and temporal persistence.

    Returns: 0.0 (safe) to 1.0 (critical)
    """
    w1, w2, w3, w4 = 0.30, 0.25, 0.20, 0.15
    w5 = 0.10  # payment + persistence

    s_severity = SEVERITY_WEIGHTS.get(severity, 0.3)
    s_deviation = min(abs(area_deviation_pct) / 30.0, 1.0)
    s_iou_dep = 1.0 - iou

    bonus = 0.0
    if payment_default:
        bonus += 0.5
    if temporal_persistence >= 3:
        bonus += 0.3
    elif temporal_persistence >= 2:
        bonus += 0.15

    score = (w1 * s_severity + w2 * s_deviation + w3 * confidence +
             w4 * s_iou_dep + w5 * min(bonus, 1.0))
    return round(min(max(score, 0.0), 1.0), 3)


def classify_severity(area_deviation_pct: float, iou: float) -> str:
    """Auto-classify severity from spatial metrics."""
    deviation = abs(area_deviation_pct)
    if deviation > 25 or iou < 0.5:
        return "critical"
    if deviation > 15 or iou < 0.65:
        return "high"
    if deviation > 8 or iou < 0.80:
        return "medium"
    return "low"


# ══════════════════════════════════════════════════════════════════
# Full Encroachment Analysis Pipeline
# ══════════════════════════════════════════════════════════════════

def analyze_plot_encroachment(
    allotted_coords: List[List[float]],
    detected_coords: List[List[float]],
    buffer_tolerance_m: float = 2.0,
) -> Dict:
    """
    Full GIS encroachment analysis for a single plot.

    Returns dict with:
        iou, area_deviation_pct, encroachment_area_sqm,
        severity, risk_score, encroachment_geojson, hausdorff_m
    """
    allotted_area = polygon_area_sqm(allotted_coords)
    detected_area = polygon_area_sqm(detected_coords)

    # Apply buffer tolerance
    buffered_allotted = buffer_polygon(allotted_coords, buffer_tolerance_m)
    buffered_area = polygon_area_sqm(buffered_allotted)

    # Intersection
    inter_coords = polygon_intersection(detected_coords, allotted_coords)
    inter_area = polygon_area_sqm(inter_coords) if inter_coords else 0.0

    # IoU
    iou = compute_iou(allotted_area, detected_area, inter_area)

    # Area deviation
    deviation = compute_area_deviation(allotted_area, detected_area)

    # Encroachment polygon
    diff_coords = polygon_difference(detected_coords, buffered_allotted)
    encroachment_area = max(0, detected_area - polygon_area_sqm(
        polygon_intersection(detected_coords, buffered_allotted) or []))

    # Hausdorff distance
    hausdorff = hausdorff_distance(allotted_coords, detected_coords)

    # Severity classification
    severity = classify_severity(deviation, iou)

    # Risk score
    risk = compute_risk_score(severity, deviation, 0.85, iou)

    # Encroachment GeoJSON
    encroach_geojson = None
    if diff_coords and len(diff_coords) >= 4:
        encroach_geojson = {
            "type": "Feature",
            "properties": {
                "type": "encroachment",
                "area_sqm": round(encroachment_area, 1),
                "severity": severity,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [diff_coords],
            }
        }

    return {
        "allotted_area_sqm": round(allotted_area, 1),
        "detected_area_sqm": round(detected_area, 1),
        "intersection_area_sqm": round(inter_area, 1),
        "iou": iou,
        "area_deviation_pct": deviation,
        "encroachment_area_sqm": round(encroachment_area, 1),
        "severity": severity,
        "risk_score": risk,
        "hausdorff_distance_m": hausdorff,
        "buffer_tolerance_m": buffer_tolerance_m,
        "encroachment_geojson": encroach_geojson,
    }


def batch_analyze_region(
    plots: List[Dict],
    detected_structures: List[Dict],
    buffer_tolerance_m: float = 2.0,
) -> Dict:
    """
    Batch encroachment analysis for all plots in a region.

    plots: list of {plot_id, boundary_coords: [[lon,lat],...]}
    detected_structures: list of {detected_coords: [[lon,lat],...], confidence}
    """
    results = []
    total_encroachment_sqm = 0.0
    severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}

    for plot in plots:
        allotted = plot.get("boundary_coords", [])
        if not allotted or len(allotted) < 4:
            continue

        # Find detected structures that overlap this plot
        best_match = None
        best_overlap = 0.0

        for ds in detected_structures:
            detected = ds.get("detected_coords", [])
            if not detected or len(detected) < 4:
                continue
            inter = polygon_intersection(detected, allotted)
            if inter:
                area = polygon_area_sqm(inter)
                if area > best_overlap:
                    best_overlap = area
                    best_match = ds

        if best_match:
            analysis = analyze_plot_encroachment(
                allotted, best_match["detected_coords"], buffer_tolerance_m)
            analysis["plot_id"] = plot.get("plot_id", "")
            analysis["confidence"] = best_match.get("confidence", 0.85)
            total_encroachment_sqm += analysis["encroachment_area_sqm"]
            severity_counts[analysis["severity"]] += 1
            results.append(analysis)

    return {
        "total_plots_analyzed": len(plots),
        "violations_found": len(results),
        "total_encroachment_sqm": round(total_encroachment_sqm, 1),
        "severity_breakdown": severity_counts,
        "plot_analyses": results,
    }
