"""
ILMCS — Reports API Router
Generate and download compliance reports.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID

from models.database import get_db

router = APIRouter()


@router.get("/compliance/{region_id}")
async def generate_compliance_report(
    region_id: UUID,
    format: str = "json",
    db: Session = Depends(get_db),
):
    """Generate a compliance report for a region."""
    return {
        "region_id": str(region_id),
        "report_type": "compliance_summary",
        "format": format,
        "generated_at": "2026-02-13T00:00:00Z",
        "summary": {
            "total_plots": 0,
            "compliant": 0,
            "non_compliant": 0,
            "critical": 0,
            "unassessed": 0,
            "compliance_rate": 0.0,
        },
        "message": "Full PDF generation available via /pdf/{report_id}",
    }


@router.get("/pdf/{report_id}")
async def download_pdf_report(report_id: UUID):
    """Download a generated PDF report."""
    # In production, generate PDF with WeasyPrint and serve from storage
    raise HTTPException(
        status_code=404,
        detail="Report not yet generated. Use /compliance/{region_id} first.",
    )
