"""
ILMCS — Encroachment Detection Service
Compare plot boundaries with detected built-up regions.
Supports ALL 56 Chhattisgarh industrial regions.
Computes IoU, area deviation %, risk scores, and activity classification.
"""

import uuid
import math
import random
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Plot data generator ───────────────────────────────────────────
# In production, boundaries come from PostGIS / uploaded GeoJSON.
# For demo: dynamically generate realistic plots per region.

# Named plots for major regions (real allottees where known)
NAMED_PLOTS = {
    "siltaraphase1": [
        {"id": "SLT1-001", "name": "Plot A-1 (Tata Steel)", "area_sqm": 12500, "lat": 21.3220, "lon": 81.6880},
        {"id": "SLT1-002", "name": "Plot A-2 (Jindal Power)", "area_sqm": 8300, "lat": 21.3190, "lon": 81.6920},
        {"id": "SLT1-003", "name": "Plot B-1 (Godawari Ispat)", "area_sqm": 15000, "lat": 21.3170, "lon": 81.6860},
        {"id": "SLT1-004", "name": "Plot B-2 (Vacant)", "area_sqm": 6200, "lat": 21.3240, "lon": 81.6910},
        {"id": "SLT1-005", "name": "Plot C-1 (Sarda Energy)", "area_sqm": 9800, "lat": 21.3210, "lon": 81.6940},
        {"id": "SLT1-006", "name": "Plot C-2 (Monnet Ispat)", "area_sqm": 11200, "lat": 21.3200, "lon": 81.6850},
        {"id": "SLT1-007", "name": "Plot D-1 (Hira Group)", "area_sqm": 7500, "lat": 21.3250, "lon": 81.6870},
        {"id": "SLT1-008", "name": "Plot D-2 (SKS Ispat)", "area_sqm": 13400, "lat": 21.3160, "lon": 81.6930},
    ],
    "siltaraphase2": [
        {"id": "SLT2-001", "name": "Plot A-1 (Jayaswal Neco)", "area_sqm": 14000, "lat": 21.3310, "lon": 81.6980},
        {"id": "SLT2-002", "name": "Plot A-2 (Vacant)", "area_sqm": 9000, "lat": 21.3290, "lon": 81.7020},
        {"id": "SLT2-003", "name": "Plot B-1 (Vandana Global)", "area_sqm": 11500, "lat": 21.3340, "lon": 81.6990},
        {"id": "SLT2-004", "name": "Plot B-2 (Balaji TMT)", "area_sqm": 7800, "lat": 21.3280, "lon": 81.7010},
        {"id": "SLT2-005", "name": "Plot C-1 (Vacant)", "area_sqm": 5500, "lat": 21.3350, "lon": 81.6970},
        {"id": "SLT2-006", "name": "Plot C-2 (Salasar Techno)", "area_sqm": 10200, "lat": 21.3260, "lon": 81.7040},
    ],
    "urla": [
        {"id": "URL-001", "name": "Plot 1 (Prakash Industries)", "area_sqm": 9000, "lat": 21.2520, "lon": 81.5790},
        {"id": "URL-002", "name": "Plot 2 (NMDC Ltd)", "area_sqm": 11000, "lat": 21.2480, "lon": 81.5810},
        {"id": "URL-003", "name": "Plot 3 (Visa Steel)", "area_sqm": 7800, "lat": 21.2510, "lon": 81.5770},
        {"id": "URL-004", "name": "Plot 4 (Vacant)", "area_sqm": 5500, "lat": 21.2490, "lon": 81.5830},
        {"id": "URL-005", "name": "Plot 5 (CG Steel)", "area_sqm": 8200, "lat": 21.2530, "lon": 81.5760},
        {"id": "URL-006", "name": "Plot 6 (Shri Bajrang)", "area_sqm": 6800, "lat": 21.2470, "lon": 81.5820},
    ],
    "borai": [
        {"id": "BOR-001", "name": "Plot 1 (SAIL Sub-plant)", "area_sqm": 20000, "lat": 21.2120, "lon": 81.3490},
        {"id": "BOR-002", "name": "Plot 2 (Bhilai Eng Corp)", "area_sqm": 15000, "lat": 21.2090, "lon": 81.3510},
        {"id": "BOR-003", "name": "Plot 3 (Vacant)", "area_sqm": 8500, "lat": 21.2140, "lon": 81.3470},
        {"id": "BOR-004", "name": "Plot 4 (Rashi Steel)", "area_sqm": 12000, "lat": 21.2110, "lon": 81.3530},
        {"id": "BOR-005", "name": "Plot 5 (Topworth Steel)", "area_sqm": 9200, "lat": 21.2080, "lon": 81.3460},
    ],
}

# Activity classification labels
ACTIVITY_LABELS = ["RUNNING", "CLOSED", "UNDER_CONSTRUCTION", "IDLE"]


def _generate_plots_for_region(region_key: str, center_lat: float, center_lon: float, n_plots: int = 8) -> List[Dict]:
    """Dynamically generate realistic plot data for a region."""
    random.seed(hash(region_key) % 2**32)
    prefix = region_key[:3].upper()
    plots = []
    for i in range(n_plots):
        area = random.choice([5000, 6000, 7500, 8000, 9000, 10000, 12000, 15000, 18000, 20000])
        lat_offset = random.uniform(-0.008, 0.008)
        lon_offset = random.uniform(-0.008, 0.008)
        is_vacant = random.random() < 0.15
        company_names = [
            "CG Industries", "Raipur Alloys", "Nava Bharat Ventures", "Godawari Power",
            "Sarda Energy", "Prakash Industries", "Jayaswal Neco", "Vandana Global",
            "Balaji TMT", "Topworth Steel", "Hira Group", "SKS Ispat",
            "Salasar Techno", "Shri Bajrang", "CG Steel", "Modern Steel",
        ]
        name = f"Plot {chr(65 + i // 4)}-{i % 4 + 1} ({'Vacant' if is_vacant else random.choice(company_names)})"
        plots.append({
            "id": f"{prefix}-{i+1:03d}",
            "name": name,
            "area_sqm": area,
            "lat": round(center_lat + lat_offset, 4),
            "lon": round(center_lon + lon_offset, 4),
        })
    return plots


def _get_plots(region_key: str) -> List[Dict]:
    """Get plots for a region — use named data if available, else generate."""
    # FORCE DYNAMIC GENERATION FOR ALL REGIONS (User Request)
    # if region_key in NAMED_PLOTS:
    #     return NAMED_PLOTS[region_key]
    
    from services.gee_service import REGION_CATALOG
    info = REGION_CATALOG.get(region_key)
    if info:
        # Generate varied number of plots for realistic density
        n = random.choice([10, 12, 15, 18])
        return _generate_plots_for_region(region_key, info["lat"], info["lon"], n)
    return _generate_plots_for_region(region_key, 21.25, 81.63, 12)


def _plot_boundary_polygon(lat: float, lon: float, area_sqm: float) -> List:
    """Generate a rectangular boundary polygon from center and area."""
    side_m = math.sqrt(area_sqm)
    half_lat = (side_m / 2) / 111320
    half_lon = (side_m / 2) / (111320 * math.cos(math.radians(lat)))
    return [
        [round(lon - half_lon, 6), round(lat - half_lat, 6)],
        [round(lon + half_lon, 6), round(lat - half_lat, 6)],
        [round(lon + half_lon, 6), round(lat + half_lat, 6)],
        [round(lon - half_lon, 6), round(lat + half_lat, 6)],
        [round(lon - half_lon, 6), round(lat - half_lat, 6)],  # Close
    ]


def _compute_iou(allotted_area: float, detected_area: float) -> float:
    """
    Compute Intersection over Union between allotted and detected areas.
    IoU = Intersection / Union
    For rectangular approximations:
      intersection = min(allotted, detected)
      union = max(allotted, detected)
    """
    if allotted_area <= 0 and detected_area <= 0:
        return 1.0
    intersection = min(allotted_area, detected_area)
    union = max(allotted_area, detected_area)
    return round(intersection / union, 4) if union > 0 else 0.0


def _compute_area_deviation(allotted_area: float, detected_area: float) -> float:
    """
    Area deviation as percentage.
    deviation = ((detected - allotted) / allotted) * 100
    Positive = over-utilization, Negative = under-utilization
    """
    if allotted_area <= 0:
        return 0.0
    return round((detected_area - allotted_area) / allotted_area * 100, 2)


def _compute_risk_score(severity: str, area_deviation_pct: float, confidence: float, iou: float) -> float:
    """
    Composite risk score between 0.0 (safe) and 1.0 (critical).
    Factors:
      - Severity weight (critical=1.0, high=0.75, medium=0.5, low=0.2)
      - Area deviation magnitude (clamped 0-1)
      - Confidence of detection
      - IoU departure from ideal (1.0 - IoU)
    """
    severity_weight = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.2}.get(severity, 0.3)
    deviation_factor = min(abs(area_deviation_pct) / 30.0, 1.0)  # 30% deviation = factor 1.0
    iou_departure = 1.0 - iou
    score = 0.35 * severity_weight + 0.25 * deviation_factor + 0.20 * confidence + 0.20 * iou_departure
    return round(min(max(score, 0.0), 1.0), 3)


def _classify_activity(plot_name: str, utilization_pct: float) -> str:
    """Classify industry activity based on utilization and name."""
    if "Vacant" in plot_name:
        return "IDLE"
    if utilization_pct < 10:
        return "CLOSED"
    if utilization_pct < 60:
        return "UNDER_CONSTRUCTION"
    return "RUNNING"


def detect_encroachments(
    region_name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    boundary_geojson: Optional[Dict] = None,
    detection_date: Optional[str] = None,
) -> Dict:
    """
    Detect encroachments by comparing plot boundaries with built-up detection.
    
    In production, this uses:
    1. PostGIS boundaries or uploaded GeoJSON
    2. ESRGAN-enhanced satellite imagery
    3. DeepLabV3+ segmentation for built-up detection
    4. Shapely geometric comparison (IoU, area deviation, buffer tolerance)

    In demo mode, returns realistic simulated results with full metrics.
    """
    # Resolve region
    key = (region_name or "siltaraphase1").lower().strip().replace(" ", "").replace("-", "").replace("_", "")
    plots = _get_plots(key)
    region_display = region_name or key.title()

    # Seed depends on key AND date (year) to show evolution over time
    seed_str = key
    if detection_date:
        # Use year to have stable status per year, but different across years
        try:
            year = detection_date.split("-")[0]
            seed_str += f"-{year}"
        except:
            seed_str += str(detection_date)
            
    random.seed(hash(seed_str) % 2**32)

    encroachments = []
    total_area = 0
    total_utilized = 0
    total_affected_area = 0.0

    for plot in plots:
        total_area += plot["area_sqm"]
        boundary = _plot_boundary_polygon(plot["lat"], plot["lon"], plot["area_sqm"])

        # Simulate detection results
        roll = random.random()

        if "Vacant" in plot["name"]:
            if roll < 0.6:
                utilized = round(random.uniform(5, 25), 1)
                detected_area = plot["area_sqm"] * utilized / 100
                total_utilized += detected_area
                affected = round(detected_area, 1)
                total_affected_area += affected
                iou = _compute_iou(plot["area_sqm"], detected_area)
                deviation = _compute_area_deviation(plot["area_sqm"], detected_area)
                sev = "medium" if utilized < 15 else "high"
                conf = round(random.uniform(0.78, 0.95), 2)
                risk = _compute_risk_score(sev, deviation, conf, iou)
                encroachments.append({
                    "plot_id": plot["id"],
                    "plot_name": plot["name"],
                    "encroachment_type": "vacant_plot",
                    "severity": sev,
                    "affected_area_sqm": affected,
                    "boundary_area_sqm": plot["area_sqm"],
                    "utilization_pct": utilized,
                    "iou_score": iou,
                    "area_deviation_pct": deviation,
                    "risk_score": risk,
                    "confidence": conf,
                    "activity_status": _classify_activity(plot["name"], utilized),
                    "description": f"Vacant plot with {utilized}% unauthorized occupation detected.",
                    "boundary": {"type": "Polygon", "coordinates": [boundary]},
                    "geometry": {"type": "Polygon", "coordinates": [boundary]},
                })
            else:
                total_utilized += 0
                iou = _compute_iou(plot["area_sqm"], 0)
                deviation = _compute_area_deviation(plot["area_sqm"], 0)
                conf = round(random.uniform(0.85, 0.98), 2)
                risk = _compute_risk_score("low", deviation, conf, iou)
                encroachments.append({
                    "plot_id": plot["id"],
                    "plot_name": plot["name"],
                    "encroachment_type": "vacant_plot",
                    "severity": "low",
                    "affected_area_sqm": 0,
                    "boundary_area_sqm": plot["area_sqm"],
                    "utilization_pct": 0,
                    "iou_score": iou,
                    "area_deviation_pct": deviation,
                    "risk_score": risk,
                    "confidence": conf,
                    "activity_status": "IDLE",
                    "description": "Plot confirmed vacant — no construction detected.",
                    "boundary": {"type": "Polygon", "coordinates": [boundary]},
                    "geometry": {"type": "Polygon", "coordinates": [boundary]},
                })

        elif roll < 0.25:
            # Construction outside boundary
            excess_pct = round(random.uniform(5, 20), 1)
            utilized = round(random.uniform(85, 110 + excess_pct), 1)
            detected_area = plot["area_sqm"] * utilized / 100
            total_utilized += min(plot["area_sqm"], detected_area)
            affected = round(plot["area_sqm"] * excess_pct / 100, 1)
            total_affected_area += affected
            iou = _compute_iou(plot["area_sqm"], detected_area)
            deviation = _compute_area_deviation(plot["area_sqm"], detected_area)
            sev = "critical" if excess_pct > 12 else "high"
            conf = round(random.uniform(0.8, 0.94), 2)
            risk = _compute_risk_score(sev, deviation, conf, iou)
            encroachments.append({
                "plot_id": plot["id"],
                "plot_name": plot["name"],
                "encroachment_type": "outside_boundary",
                "severity": sev,
                "affected_area_sqm": affected,
                "boundary_area_sqm": plot["area_sqm"],
                "utilization_pct": utilized,
                "iou_score": iou,
                "area_deviation_pct": deviation,
                "risk_score": risk,
                "confidence": conf,
                "activity_status": _classify_activity(plot["name"], utilized),
                "description": f"Construction exceeds boundary by {excess_pct}% ({round(plot['area_sqm'] * excess_pct / 100)} m²).",
                "boundary": {"type": "Polygon", "coordinates": [boundary]},
                "geometry": {"type": "Polygon", "coordinates": [boundary]},
            })

        elif roll < 0.45:
            # Partial construction
            utilized = round(random.uniform(30, 70), 1)
            detected_area = plot["area_sqm"] * utilized / 100
            total_utilized += detected_area
            affected = round(plot["area_sqm"] * (100 - utilized) / 100, 1)
            total_affected_area += affected
            iou = _compute_iou(plot["area_sqm"], detected_area)
            deviation = _compute_area_deviation(plot["area_sqm"], detected_area)
            conf = round(random.uniform(0.75, 0.92), 2)
            risk = _compute_risk_score("medium", deviation, conf, iou)
            encroachments.append({
                "plot_id": plot["id"],
                "plot_name": plot["name"],
                "encroachment_type": "partial_construction",
                "severity": "medium",
                "affected_area_sqm": affected,
                "boundary_area_sqm": plot["area_sqm"],
                "utilization_pct": utilized,
                "iou_score": iou,
                "area_deviation_pct": deviation,
                "risk_score": risk,
                "confidence": conf,
                "activity_status": _classify_activity(plot["name"], utilized),
                "description": f"Only {utilized}% of allocated area utilized. Remaining area idle.",
                "boundary": {"type": "Polygon", "coordinates": [boundary]},
                "geometry": {"type": "Polygon", "coordinates": [boundary]},
            })

        else:
            # Compliant
            utilized = round(random.uniform(80, 100), 1)
            total_utilized += plot["area_sqm"] * utilized / 100

    overall_util = round(total_utilized / total_area * 100, 1) if total_area > 0 else 0

    # Compliance category based on encroachment count and severity
    critical_count = sum(1 for e in encroachments if e["severity"] == "critical")
    high_count = sum(1 for e in encroachments if e["severity"] == "high")
    if critical_count > 0:
        compliance_category = "CRITICAL"
    elif high_count > 0:
        compliance_category = "NON_COMPLIANT"
    elif len(encroachments) > 0:
        compliance_category = "MINOR_ISSUES"
    else:
        compliance_category = "COMPLIANT"

    # Overall compliance score (0-100)
    avg_risk = sum(e["risk_score"] for e in encroachments) / max(len(encroachments), 1)
    compliance_score = round(max(0, 100 - avg_risk * 100), 1)

    return {
        "region_name": region_display,
        "total_plots": len(plots),
        "encroachments_found": len(encroachments),
        "encroachments": encroachments,
        "overall_utilization_pct": overall_util,
        "total_affected_area_sqm": round(total_affected_area, 1),
        "compliance_score": compliance_score,
        "compliance_category": compliance_category,
        "avg_iou": round(sum(e["iou_score"] for e in encroachments) / max(len(encroachments), 1), 4),
        "avg_risk_score": round(avg_risk, 3),
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "boundary_geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                        "properties": {
                            "id": p["id"],
                            "name": p["name"],
                            "area_sqm": p["area_sqm"],
                            "status": next(
                                (e["encroachment_type"] for e in encroachments if e["plot_id"] == p["id"]),
                                "compliant"
                            ),
                            "latitude": p["lat"],
                            "longitude": p["lon"],
                        },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [_plot_boundary_polygon(p["lat"], p["lon"], p["area_sqm"])],
                    },
                }
                for p in plots
            ],
        },
    }
