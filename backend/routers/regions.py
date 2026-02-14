"""
ILMCS — Regions API Router
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.functions import ST_AsGeoJSON, ST_Transform, ST_Area
from typing import Optional
from uuid import UUID

from models.database import get_db, IndustrialRegion, Plot

router = APIRouter()


@router.get("/")
async def list_regions(
    type: Optional[str] = Query(None, description="Filter by type: NEW or OLD"),
    district: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all industrial regions with summary stats."""
    query = db.query(IndustrialRegion)
    if type:
        query = query.filter(IndustrialRegion.type == type.upper())
    if district:
        query = query.filter(IndustrialRegion.district.ilike(f"%{district}%"))

    regions = query.order_by(IndustrialRegion.name).all()
    return {
        "total": len(regions),
        "regions": [
            {
                "region_id": str(r.region_id),
                "name": r.name,
                "code": r.code,
                "type": r.type,
                "district": r.district,
                "total_plots": r.total_plots,
                "centroid": {"lat": r.centroid_lat, "lon": r.centroid_lon},
            }
            for r in regions
        ],
    }


@router.get("/{region_id}")
async def get_region(region_id: UUID, db: Session = Depends(get_db)):
    """Get detailed information about a region including GeoJSON boundary."""
    region = db.query(IndustrialRegion).filter(
        IndustrialRegion.region_id == region_id
    ).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    boundary_geojson = None
    if region.boundary_geom:
        boundary_geojson = db.query(
            ST_AsGeoJSON(region.boundary_geom)
        ).scalar()

    return {
        "region_id": str(region.region_id),
        "name": region.name,
        "code": region.code,
        "type": region.type,
        "state": region.state,
        "district": region.district,
        "total_plots": region.total_plots,
        "boundary_geojson": boundary_geojson,
        "centroid": {"lat": region.centroid_lat, "lon": region.centroid_lon},
        "established_date": str(region.established_date) if region.established_date else None,
    }


@router.get("/{region_id}/plots")
async def list_region_plots(
    region_id: UUID,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all plots in a region with pagination."""
    query = db.query(Plot).filter(Plot.region_id == region_id)
    if status:
        query = query.filter(Plot.plot_status == status.upper())

    total = query.count()
    plots = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "region_id": str(region_id),
        "total": total,
        "page": page,
        "limit": limit,
        "plots": [
            {
                "plot_id": str(p.plot_id),
                "plot_number": p.plot_number,
                "allottee_name": p.allottee_name,
                "status": p.plot_status,
                "approved_purpose": p.approved_purpose,
                "allotment_date": str(p.allotment_date) if p.allotment_date else None,
            }
            for p in plots
        ],
    }


@router.get("/summary/stats")
async def region_summary_stats(db: Session = Depends(get_db)):
    """Get summary statistics across all regions."""
    total = db.query(func.count(IndustrialRegion.region_id)).scalar()
    new_count = db.query(func.count(IndustrialRegion.region_id)).filter(
        IndustrialRegion.type == 'NEW'
    ).scalar()
    old_count = db.query(func.count(IndustrialRegion.region_id)).filter(
        IndustrialRegion.type == 'OLD'
    ).scalar()
    total_plots = db.query(func.sum(IndustrialRegion.total_plots)).scalar() or 0

    return {
        "total_regions": total,
        "new_regions": new_count,
        "old_regions": old_count,
        "total_plots": total_plots,
    }
