"""
ILMCS — Violations API Router
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from models.database import get_db, Violation

router = APIRouter()


@router.get("/")
async def list_violations(
    severity: Optional[str] = None,
    violation_type: Optional[str] = None,
    status: Optional[str] = None,
    min_risk: Optional[float] = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List violations with filtering and pagination."""
    query = db.query(Violation)

    if severity:
        query = query.filter(Violation.severity == severity.upper())
    if violation_type:
        query = query.filter(Violation.violation_type == violation_type.upper())
    if status:
        query = query.filter(Violation.status == status.upper())
    if min_risk is not None:
        query = query.filter(Violation.risk_score >= min_risk)

    total = query.count()
    violations = (
        query.order_by(Violation.risk_score.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "violations": [
            {
                "violation_id": str(v.violation_id),
                "plot_id": str(v.plot_id),
                "type": v.violation_type,
                "severity": v.severity,
                "status": v.status,
                "risk_score": v.risk_score,
                "iou_score": v.iou_score,
                "encroachment_area_sqm": v.encroachment_area_sqm,
                "area_deviation_pct": v.area_deviation_pct,
                "confidence": v.confidence_score,
                "detected_at": str(v.detected_at),
            }
            for v in violations
        ],
    }


@router.get("/{violation_id}")
async def get_violation(violation_id: UUID, db: Session = Depends(get_db)):
    """Get detailed violation information with evidence."""
    v = db.query(Violation).filter(Violation.violation_id == violation_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Violation not found")

    return {
        "violation_id": str(v.violation_id),
        "plot_id": str(v.plot_id),
        "type": v.violation_type,
        "severity": v.severity,
        "status": v.status,
        "risk_score": v.risk_score,
        "iou_score": v.iou_score,
        "encroachment_area_sqm": v.encroachment_area_sqm,
        "area_deviation_pct": v.area_deviation_pct,
        "confidence": v.confidence_score,
        "evidence_image": v.evidence_image_path,
        "overlay_image": v.overlay_image_path,
        "detected_at": str(v.detected_at),
        "confirmed_at": str(v.confirmed_at) if v.confirmed_at else None,
        "reviewed_by": v.reviewed_by,
        "review_notes": v.review_notes,
        "auto_detected": v.auto_detected,
        "false_positive": v.false_positive,
    }


@router.patch("/{violation_id}")
async def update_violation_status(
    violation_id: UUID,
    status: str = Query(..., description="New status"),
    reviewed_by: Optional[str] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Update violation status (review workflow)."""
    v = db.query(Violation).filter(Violation.violation_id == violation_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Violation not found")

    valid_statuses = [
        'DETECTED', 'CONFIRMED', 'UNDER_REVIEW',
        'NOTICE_ISSUED', 'RESOLVED', 'DISMISSED',
        'ESCALATED', 'LEGAL_ACTION',
    ]
    if status.upper() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    v.status = status.upper()
    if reviewed_by:
        v.reviewed_by = reviewed_by
    if notes:
        v.review_notes = notes

    from datetime import datetime
    if status.upper() == 'CONFIRMED':
        v.confirmed_at = datetime.utcnow()
    elif status.upper() == 'RESOLVED':
        v.resolved_at = datetime.utcnow()
    elif status.upper() == 'DISMISSED':
        v.false_positive = True

    db.commit()
    return {"status": "updated", "violation_id": str(violation_id), "new_status": v.status}
