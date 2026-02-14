# ILMCS — GIS Engine Module
from .spatial_analysis import (
    compute_iou,
    compute_iou_from_areas,
    compute_area_deviation,
    compute_risk_score,
    classify_severity,
    polygon_area_sqm,
    polygon_centroid,
    polygon_intersection,
    polygon_difference,
    buffer_polygon,
    hausdorff_distance,
    point_in_polygon,
    analyze_plot_encroachment,
    batch_analyze_region,
)
from .violations import (
    create_violation,
    get_violations,
    update_violation_status,
    get_alerts,
    generate_region_violations,
    VIOLATION_TYPES,
    SEVERITY_LABELS,
)

__all__ = [
    "compute_iou", "compute_iou_from_areas", "compute_area_deviation",
    "compute_risk_score", "classify_severity",
    "polygon_area_sqm", "polygon_centroid",
    "polygon_intersection", "polygon_difference",
    "buffer_polygon", "hausdorff_distance", "point_in_polygon",
    "analyze_plot_encroachment", "batch_analyze_region",
    "create_violation", "get_violations", "update_violation_status",
    "get_alerts", "generate_region_violations",
    "VIOLATION_TYPES", "SEVERITY_LABELS",
]
