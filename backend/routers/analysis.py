"""
ILMCS — Analysis API Router
Trigger and monitor satellite analysis jobs.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from datetime import datetime

from models.database import get_db

router = APIRouter()


@router.post("/trigger")
async def trigger_analysis(
    region_id: UUID,
    analysis_type: str = "FULL_ANALYSIS",
    db: Session = Depends(get_db),
):
    """Trigger a satellite analysis job for a region."""
    job_id = uuid4()
    # In production, this would enqueue a Celery task
    return {
        "job_id": str(job_id),
        "region_id": str(region_id),
        "type": analysis_type,
        "status": "QUEUED",
        "message": "Analysis job queued. Use /status/{job_id} to track progress.",
    }


@router.get("/status/{job_id}")
async def get_analysis_status(job_id: UUID, db: Session = Depends(get_db)):
    """Get the status of an analysis job."""
    return {
        "job_id": str(job_id),
        "status": "RUNNING",
        "progress_pct": 45.0,
        "started_at": datetime.utcnow().isoformat(),
    }


@router.get("/results/{job_id}")
async def get_analysis_results(job_id: UUID, db: Session = Depends(get_db)):
    """Get the results of a completed analysis job."""
    return {
        "job_id": str(job_id),
        "status": "COMPLETED",
        "results": {
            "plots_analyzed": 0,
            "violations_found": 0,
            "new_violations": 0,
            "resolved_violations": 0,
        },
    }
