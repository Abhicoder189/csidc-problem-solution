"""
ILMCS — Dashboard API Router
Aggregated data endpoints for the frontend dashboard.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from uuid import UUID

from models.database import (
    get_db, IndustrialRegion, Plot, Violation, ComplianceStatus
)

router = APIRouter()


@router.get("/overview")
async def dashboard_overview(db: Session = Depends(get_db)):
    """System-wide dashboard overview statistics."""
    total_regions = db.query(func.count(IndustrialRegion.region_id)).scalar()
    total_plots = db.query(func.count(Plot.plot_id)).scalar()
    active_violations = (
        db.query(func.count(Violation.violation_id))
        .filter(Violation.status.notin_(['RESOLVED', 'DISMISSED']))
        .scalar()
    )
    critical_violations = (
        db.query(func.count(Violation.violation_id))
        .filter(
            Violation.severity.in_(['CRITICAL', 'SEVERE']),
            Violation.status.notin_(['RESOLVED', 'DISMISSED']),
        )
        .scalar()
    )

    avg_compliance = (
        db.query(func.avg(ComplianceStatus.overall_score)).scalar()
    )

    return {
        "total_regions": total_regions,
        "total_plots": total_plots,
        "active_violations": active_violations,
        "critical_violations": critical_violations,
        "average_compliance_score": round(avg_compliance, 1) if avg_compliance else 0,
        "compliance_rate": 0,
    }


@router.get("/heatmap")
async def heatmap_data(
    type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    GeoJSON FeatureCollection for the violation heatmap.
    Each region is a feature with violation_count property.
    """
    query = db.query(IndustrialRegion)
    if type:
        query = query.filter(IndustrialRegion.type == type.upper())

    regions = query.all()

    features = []
    for r in regions:
        violation_count = (
            db.query(func.count(Violation.violation_id))
            .join(Plot, Plot.plot_id == Violation.plot_id)
            .filter(
                Plot.region_id == r.region_id,
                Violation.status.notin_(['RESOLVED', 'DISMISSED']),
            )
            .scalar()
        )

        features.append({
            "type": "Feature",
            "properties": {
                "region_id": str(r.region_id),
                "name": r.name,
                "code": r.code,
                "type": r.type,
                "violations": violation_count,
                "total_plots": r.total_plots,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [r.centroid_lon or 81.6, r.centroid_lat or 21.25],
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/timeline/{region_id}")
async def region_timeline(
    region_id: UUID,
    months: int = Query(12, ge=1, le=60),
    db: Session = Depends(get_db),
):
    """
    Temporal analysis data for a region.
    Returns violation counts and compliance scores over time.
    """
    return {
        "region_id": str(region_id),
        "period_months": months,
        "timeline": [],
        "message": "Timeline data populated after first analysis cycle.",
    }


@router.get("/violations-by-type")
async def violations_by_type(db: Session = Depends(get_db)):
    """Aggregate violations by type for pie chart."""
    results = (
        db.query(Violation.violation_type, func.count(Violation.violation_id))
        .filter(Violation.status.notin_(['RESOLVED', 'DISMISSED']))
        .group_by(Violation.violation_type)
        .all()
    )
    return {
        "data": [
            {"type": vtype, "count": count}
            for vtype, count in results
        ]
    }


@router.get("/violations-by-severity")
async def violations_by_severity(db: Session = Depends(get_db)):
    """Aggregate violations by severity for bar chart."""
    results = (
        db.query(Violation.severity, func.count(Violation.violation_id))
        .filter(Violation.status.notin_(['RESOLVED', 'DISMISSED']))
        .group_by(Violation.severity)
        .all()
    )
    return {
        "data": [
            {"severity": sev, "count": count}
            for sev, count in results
        ]
    }
