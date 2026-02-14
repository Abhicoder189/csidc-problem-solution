"""
ILMCS — PDF Report Generator
Generates downloadable compliance reports using FPDF2.
"""

import os
import uuid
import io
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    logger.warning("fpdf2 not installed — PDF reports will be plain text")


REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


class ILMCSReport(FPDF if FPDF_AVAILABLE else object):
    """Government-style compliance report."""

    def __init__(self):
        if FPDF_AVAILABLE:
            super().__init__()
            self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if not FPDF_AVAILABLE:
            return
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "INDUSTRIAL LAND MONITORING & COMPLIANCE SYSTEM", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Government of Chhattisgarh | CSIDC", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        if not FPDF_AVAILABLE:
            return
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")


def generate_report(
    region_name: str = "All Regions",
    encroachment_data: Optional[Dict] = None,
    change_data: Optional[Dict] = None,
) -> Dict:
    """
    Generate a PDF compliance report.
    Returns report metadata with file path.
    """
    report_id = str(uuid.uuid4())
    filename = f"ILMCS_Report_{region_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = REPORTS_DIR / filename

    if FPDF_AVAILABLE:
        pdf = ILMCSReport()
        pdf.alias_nb_pages()
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"Compliance Report: {region_name}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # Summary
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "1. Executive Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6,
            f"This report presents the automated monitoring and compliance analysis "
            f"for {region_name} as of {datetime.now().strftime('%B %d, %Y')}. "
            f"The analysis uses Sentinel-2 satellite imagery with AI-powered super-resolution "
            f"(ESRGAN) and automated change detection algorithms."
        )
        pdf.ln(4)

        # Encroachment Section
        if encroachment_data:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "2. Encroachment Detection Results", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, f"Total Plots Analyzed: {encroachment_data.get('total_plots', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, f"Encroachments Found: {encroachment_data.get('encroachments_found', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, f"Overall Utilization: {encroachment_data.get('overall_utilization_pct', 'N/A')}%", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

            # Table header
            encroachments = encroachment_data.get("encroachments", [])
            if encroachments:
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(30, 7, "Plot ID", border=1)
                pdf.cell(50, 7, "Type", border=1)
                pdf.cell(25, 7, "Severity", border=1)
                pdf.cell(30, 7, "Area (m²)", border=1)
                pdf.cell(30, 7, "Util %", border=1)
                pdf.cell(25, 7, "Confidence", border=1)
                pdf.ln()

                pdf.set_font("Helvetica", "", 8)
                for e in encroachments[:15]:
                    pdf.cell(30, 6, str(e.get("plot_id", "")), border=1)
                    pdf.cell(50, 6, str(e.get("encroachment_type", "")), border=1)
                    pdf.cell(25, 6, str(e.get("severity", "")), border=1)
                    pdf.cell(30, 6, str(e.get("affected_area_sqm", "")), border=1)
                    pdf.cell(30, 6, str(e.get("utilization_pct", "")), border=1)
                    pdf.cell(25, 6, str(e.get("confidence", "")), border=1)
                    pdf.ln()
            pdf.ln(4)

        # Change Detection Section
        if change_data:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "3. Change Detection Results", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, f"Period: {change_data.get('date_before', 'N/A')} to {change_data.get('date_after', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, f"Changed Area: {change_data.get('changed_area_pct', 'N/A')}% ({change_data.get('changed_area_sqm', 'N/A')} m²)", new_x="LMARGIN", new_y="NEXT")
            if change_data.get("ndvi_change") is not None:
                pdf.cell(0, 6, f"NDVI Change: {change_data['ndvi_change']}", new_x="LMARGIN", new_y="NEXT")
            if change_data.get("built_up_after_pct") is not None:
                pdf.cell(0, 6, f"Built-up Area: {change_data.get('built_up_before_pct')}% → {change_data['built_up_after_pct']}%", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

        # Recommendations
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "4. Recommendations", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        recommendations = [
            "Conduct ground-truth verification for all critical-severity encroachments.",
            "Issue show-cause notices for construction outside allotted boundaries.",
            "Review utilization status of vacant plots for potential reallocation.",
            "Schedule quarterly satellite monitoring for high-risk areas.",
            "Update PostGIS boundary records with latest survey data.",
        ]
        for i, rec in enumerate(recommendations, 1):
            pdf.cell(0, 6, f"  {i}. {rec}", new_x="LMARGIN", new_y="NEXT")

        # Output PDF to bytes
        try:
            pdf_bytes = pdf.output(dest='S').encode('latin-1')  # 'S' returns the document as a string
            return pdf_bytes
        except Exception as e:
            # Fallback for newer fpdf2 versions or if encoding fails
            byte_stream = io.BytesIO()
            pdf.output(byte_stream)
            return byte_stream.getvalue()
    else:
        # Plain text fallback
        report_content = (
            f"ILMCS Compliance Report\n"
            f"Region: {region_name}\n"
            f"Generated: {datetime.now().isoformat()}\n\n"
            f"--- Executive Summary ---\n"
            f"This report presents the automated monitoring and compliance analysis "
            f"for {region_name} as of {datetime.now().strftime('%B %d, %Y')}. "
            f"The analysis uses Sentinel-2 satellite imagery with AI-powered super-resolution "
            f"(ESRGAN) and automated change detection algorithms.\n\n"
        )
        if encroachment_data:
            report_content += f"--- Encroachment Detection Results ---\n"
            report_content += f"Total Plots Analyzed: {encroachment_data.get('total_plots', 'N/A')}\n"
            report_content += f"Encroachments Found: {encroachment_data.get('encroachments_found', 'N/A')}\n"
            report_content += f"Overall Utilization: {encroachment_data.get('overall_utilization_pct', 'N/A')}%\n\n"
        if change_data:
            report_content += f"--- Change Detection Results ---\n"
            report_content += f"Period: {change_data.get('date_before', 'N/A')} to {change_data.get('date_after', 'N/A')}\n"
            report_content += f"Changed Area: {change_data.get('changed_area_pct', 'N/A')}% ({change_data.get('changed_area_sqm', 'N/A')} m²)\n"
            if change_data.get("ndvi_change") is not None:
                report_content += f"NDVI Change: {change_data['ndvi_change']}\n"
            if change_data.get("built_up_after_pct") is not None:
                report_content += f"Built-up Area: {change_data.get('built_up_before_pct')}% -> {change_data['built_up_after_pct']}%\n"
            report_content += "\n"
        report_content += f"--- Recommendations ---\n"
        recommendations = [
            "Conduct ground-truth verification for all critical-severity encroachments.",
            "Issue show-cause notices for construction outside allotted boundaries.",
            "Review utilization status of vacant plots for potential reallocation.",
            "Schedule quarterly satellite monitoring for high-risk areas.",
            "Update PostGIS boundary records with latest survey data.",
        ]
        for i, rec in enumerate(recommendations, 1):
            report_content += f"  {i}. {rec}\n"
        return report_content.encode('utf-8')
