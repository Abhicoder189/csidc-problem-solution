"""
ILMCS — Plots API Router
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_AsGeoJSON
from typing import Optional
from uuid import UUID

from models.database import get_db, Plot, AllotmentBoundary, ComplianceStatus, Violation

router = APIRouter()


@router.get("/{plot_id}")
async def get_plot(plot_id: UUID, db: Session = Depends(get_db)):
    """Get full plot details including boundary, compliance, and violation count."""
    plot = db.query(Plot).filter(Plot.plot_id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found")

    boundary_geojson = None
    if plot.boundary and plot.boundary.geom:
        boundary_geojson = db.query(ST_AsGeoJSON(plot.boundary.geom)).scalar()

    compliance = plot.compliance
    active_violations = (
        db.query(Violation)
        .filter(
            Violation.plot_id == plot_id,
            Violation.status.notin_(['RESOLVED', 'DISMISSED']),
        )
        .count()
    )

    return {
        "plot_id": str(plot.plot_id),
        "region_id": str(plot.region_id),
        "plot_number": plot.plot_number,
        "allottee_name": plot.allottee_name,
        "allottee_entity": plot.allottee_entity,
        "allotment_date": str(plot.allotment_date) if plot.allotment_date else None,
        "lease_type": plot.lease_type,
        "lease_expiry": str(plot.lease_expiry) if plot.lease_expiry else None,
        "approved_purpose": plot.approved_purpose,
        "status": plot.plot_status,
        "boundary_geojson": boundary_geojson,
        "compliance": {
            "overall_score": compliance.overall_score if compliance else None,
            "category": compliance.category if compliance else "UNASSESSED",
            "active_violations": active_violations,
            "last_assessed": str(compliance.last_assessed_at) if compliance and compliance.last_assessed_at else None,
        },
    }


@router.get("/{plot_id}/boundary")
async def get_plot_boundary(plot_id: UUID, db: Session = Depends(get_db)):
    """Get the allotment boundary as GeoJSON."""
    boundary = (
        db.query(AllotmentBoundary)
        .filter(AllotmentBoundary.plot_id == plot_id, AllotmentBoundary.is_active.is_(True))
        .first()
    )
    if not boundary:
        raise HTTPException(status_code=404, detail="Boundary not found")

    geojson = db.query(ST_AsGeoJSON(boundary.geom)).scalar()
    return {
        "plot_id": str(plot_id),
        "boundary_id": str(boundary.boundary_id),
        "geojson": geojson,
        "source_type": boundary.source_type,
        "accuracy_m": boundary.accuracy_m,
        "verified": boundary.verified,
        "version": boundary.version,
    }


@router.get("/{plot_id}/violations")
async def get_plot_violations(
    plot_id: UUID,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get all violations for a plot."""
    query = db.query(Violation).filter(Violation.plot_id == plot_id)
    if status:
        query = query.filter(Violation.status == status.upper())

    violations = query.order_by(Violation.detected_at.desc()).all()

    return {
        "plot_id": str(plot_id),
        "total": len(violations),
        "violations": [
            {
                "violation_id": str(v.violation_id),
                "type": v.violation_type,
                "severity": v.severity,
                "status": v.status,
                "risk_score": v.risk_score,
                "iou_score": v.iou_score,
                "encroachment_area_sqm": v.encroachment_area_sqm,
                "area_deviation_pct": v.area_deviation_pct,
                "confidence": v.confidence_score,
                "detected_at": str(v.detected_at),
                "auto_detected": v.auto_detected,
            }
            for v in violations
        ],
    }
