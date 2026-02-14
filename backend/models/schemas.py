"""
ILMCS Backend — Pydantic Schemas
Request/Response models for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────
class EncroachmentType(str, Enum):
    OUTSIDE_BOUNDARY = "outside_boundary"
    VACANT_PLOT = "vacant_plot"
    PARTIAL_CONSTRUCTION = "partial_construction"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Imagery ────────────────────────────────────────────────────────
class FetchImageryRequest(BaseModel):
    region_name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    cloud_cover_max: int = Field(20, ge=0, le=100)
    bbox_km: float = Field(5.0, ge=0.5, le=50.0, description="Bounding box half-width in km")


class ImageryResponse(BaseModel):
    region_name: str
    center: Dict[str, float]
    bbox: Dict[str, float]
    acquisition_date: str
    cloud_cover: float
    bands: List[str]
    image_url: str
    thumbnail_url: str
    ndvi_url: Optional[str] = None
    metadata: Dict[str, Any] = {}


# ── Enhancement ────────────────────────────────────────────────────
class EnhanceImageRequest(BaseModel):
    image_url: Optional[str] = None
    image_id: Optional[str] = None
    scale_factor: int = Field(4, ge=2, le=8)


class EnhanceImageResponse(BaseModel):
    original_url: str
    enhanced_url: str
    original_resolution: str
    enhanced_resolution: str
    scale_factor: int
    processing_time_ms: int
    model: str = "ESRGAN"


# ── Change Detection ──────────────────────────────────────────────
class ChangeDetectionRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    date_before: str
    date_after: str
    bbox_km: float = Field(5.0, ge=0.5, le=50.0)
    methods: List[str] = Field(
        default=["image_diff", "ndvi", "built_up"],
        description="Detection methods to apply",
    )


class ChangeDetectionResponse(BaseModel):
    center: Dict[str, float]
    date_before: str
    date_after: str
    image_before_url: str
    image_after_url: str
    change_map_url: str
    ndvi_before: Optional[float] = None
    ndvi_after: Optional[float] = None
    ndvi_change: Optional[float] = None
    built_up_before_pct: Optional[float] = None
    built_up_after_pct: Optional[float] = None
    changed_area_pct: float
    changed_area_sqm: float
    methods_applied: List[str]
    change_overlay_geojson: Optional[Dict] = None


# ── Encroachment ───────────────────────────────────────────────────
class EncroachmentRequest(BaseModel):
    region_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    boundary_geojson: Optional[Dict] = None
    detection_date: Optional[str] = None


class EncroachmentResult(BaseModel):
    plot_id: str
    plot_name: str
    encroachment_type: EncroachmentType
    severity: AlertSeverity
    affected_area_sqm: float
    boundary_area_sqm: float
    utilization_pct: float
    confidence: float
    description: str
    geometry: Optional[Dict] = None


class EncroachmentResponse(BaseModel):
    region_name: str
    total_plots: int
    encroachments_found: int
    encroachments: List[EncroachmentResult]
    overall_utilization_pct: float
    scan_date: str


# ── Report ─────────────────────────────────────────────────────────
class GenerateReportRequest(BaseModel):
    region_name: Optional[str] = "All Regions"
    include_change_detection: bool = True
    include_encroachment: bool = True
    include_imagery: bool = True
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None


class ReportResponse(BaseModel):
    report_id: str
    filename: str
    download_url: str
    generated_at: str
    pages: int
    file_size_kb: int


# ── Dashboard ──────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_regions: int
    total_plots: int
    active_alerts: int
    critical_alerts: int
    avg_utilization_pct: float
    newly_detected_structures: int
    encroachment_alerts: List[Dict[str, Any]]
    utilization_by_region: List[Dict[str, Any]]


# ── Search ─────────────────────────────────────────────────────────
class RegionSearchResult(BaseModel):
    region_id: str
    name: str
    code: str
    type: str
    district: str
    latitude: float
    longitude: float
    total_plots: int
    area_hectares: float


# ── Plot History ───────────────────────────────────────────────────
class PlotHistoryRequest(BaseModel):
    plot_id: str
    plot_geojson: Dict[str, Any]
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    num_snapshots: int = Field(6, ge=2, le=12, description="Number of historical snapshots to fetch")


class PlotSnapshotData(BaseModel):
    date: str
    actual_date: str
    days_diff: int
    image_url: str
    ndvi: float
    built_up_percentage: float
    vegetation_percentage: float


class PlotHistoryResponse(BaseModel):
    success: bool
    plot_id: str
    snapshots: List[Dict[str, Any]]
    change_points: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]] = []
    summary: Dict[str, Any]
    error: Optional[str] = None
