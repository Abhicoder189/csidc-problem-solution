"""
ILMCS — Violation Detection & Management
Production-grade violation tracking, classification, and alerting.
"""

import math
import uuid
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Violation Types ───────────────────────────────────────────────
VIOLATION_TYPES = {
    "encroachment": {
        "label": "Boundary Encroachment",
        "description": "Construction detected beyond allotted boundary",
        "base_severity": "high",
        "legal_section": "CG Industrial Development Act, Section 14(2)",
        "penalty_range": "₹50,000 – ₹5,00,000 + demolition order",
    },
    "unauthorized_construction": {
        "label": "Unauthorized Construction",
        "description": "New structure without approved building plan",
        "base_severity": "critical",
        "legal_section": "CG Industrial Policy 2019, Clause 8.3",
        "penalty_range": "₹1,00,000 – ₹10,00,000 + FIR",
    },
    "vacant_unused": {
        "label": "Vacant / Unused Plot",
        "description": "Allotted plot not utilized within stipulated period",
        "base_severity": "medium",
        "legal_section": "Allotment Terms & Conditions, Clause 5",
        "penalty_range": "Lease cancellation after 3 years idle",
    },
    "boundary_deviation": {
        "label": "Boundary Deviation",
        "description": "Actual usage boundary deviates from allotted boundary",
        "base_severity": "medium",
        "legal_section": "CSIDC Plot Allotment Rules, Rule 12",
        "penalty_range": "Survey fee + boundary restoration order",
    },
    "land_use_violation": {
        "label": "Land Use Violation",
        "description": "Plot used for purpose other than allotted category",
        "base_severity": "high",
        "legal_section": "CG Land Revenue Code, Section 170B",
        "penalty_range": "₹2,00,000 + re-category or cancellation",
    },
    "partial_construction": {
        "label": "Partial / Stalled Construction",
        "description": "Construction started but not completed within timeline",
        "base_severity": "low",
        "legal_section": "Allotment Extension Policy, Clause 3",
        "penalty_range": "Extension fee or lease cancellation",
    },
}

# ── Severity escalation matrix ────────────────────────────────────
SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
SEVERITY_LABELS = {
    "low": {"label": "Low", "color": "#22c55e", "action": "Monitor"},
    "medium": {"label": "Medium", "color": "#f59e0b", "action": "Review within 30 days"},
    "high": {"label": "High", "color": "#f97316", "action": "Issue show-cause notice"},
    "critical": {"label": "Critical", "color": "#ef4444", "action": "Immediate enforcement action"},
}


# ── In-memory violation store (demo) ──────────────────────────────
_violations_db: Dict[str, Dict] = {}
_alert_queue: List[Dict] = []


def create_violation(
    plot_id: str,
    region_id: str,
    violation_type: str,
    severity: str,
    iou_score: float = 0.0,
    area_deviation_pct: float = 0.0,
    encroachment_area_sqm: float = 0.0,
    risk_score: float = 0.0,
    confidence: float = 0.85,
    description: str = "",
    violation_polygon: Optional[Dict] = None,
    snapshot_date: Optional[str] = None,
    assigned_to: Optional[str] = None,
) -> Dict:
    """Create a new violation record."""
    vid = str(uuid.uuid4())
    vtype = VIOLATION_TYPES.get(violation_type, VIOLATION_TYPES["encroachment"])

    violation = {
        "id": vid,
        "plot_id": plot_id,
        "region_id": region_id,
        "violation_type": violation_type,
        "violation_label": vtype["label"],
        "severity": severity,
        "severity_info": SEVERITY_LABELS.get(severity, SEVERITY_LABELS["medium"]),
        "legal_section": vtype["legal_section"],
        "penalty_range": vtype["penalty_range"],
        "iou_score": round(iou_score, 4),
        "area_deviation_pct": round(area_deviation_pct, 2),
        "encroachment_area_sqm": round(encroachment_area_sqm, 1),
        "risk_score": round(risk_score, 3),
        "confidence": round(confidence, 3),
        "status": "open",
        "assigned_to": assigned_to,
        "description": description or vtype["description"],
        "violation_polygon": violation_polygon,
        "evidence_urls": [],
        "detected_at": snapshot_date or datetime.now().isoformat(),
        "acknowledged_at": None,
        "resolved_at": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "audit_trail": [{
            "action": "created",
            "by": "ILMCS_AUTO",
            "at": datetime.now().isoformat(),
            "note": f"Auto-detected {vtype['label']} with {confidence*100:.0f}% confidence",
        }],
    }

    _violations_db[vid] = violation

    # Auto-generate alert for high/critical
    if SEVERITY_ORDER.get(severity, 0) >= 2:
        _alert_queue.append({
            "id": str(uuid.uuid4()),
            "violation_id": vid,
            "plot_id": plot_id,
            "region_id": region_id,
            "severity": severity,
            "type": violation_type,
            "message": f"{vtype['label']} detected on plot {plot_id}",
            "action_required": SEVERITY_LABELS[severity]["action"],
            "created_at": datetime.now().isoformat(),
            "read": False,
        })

    return violation


def get_violations(
    region_id: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict:
    """Query violations with filters."""
    results = list(_violations_db.values())

    if region_id:
        results = [v for v in results if v["region_id"] == region_id]
    if status:
        results = [v for v in results if v["status"] == status]
    if severity:
        results = [v for v in results if v["severity"] == severity]

    # Sort by severity (critical first) then by date
    results.sort(key=lambda v: (-SEVERITY_ORDER.get(v["severity"], 0), v["detected_at"]),
                 reverse=False)

    total = len(results)
    page = results[offset:offset + limit]

    severity_summary = {}
    for v in results:
        s = v["severity"]
        severity_summary[s] = severity_summary.get(s, 0) + 1

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "severity_summary": severity_summary,
        "violations": page,
    }


def update_violation_status(violation_id: str, new_status: str, by: str = "system", note: str = "") -> Optional[Dict]:
    """Update violation status with audit trail."""
    v = _violations_db.get(violation_id)
    if not v:
        return None

    old_status = v["status"]
    v["status"] = new_status
    v["updated_at"] = datetime.now().isoformat()

    if new_status == "acknowledged":
        v["acknowledged_at"] = datetime.now().isoformat()
    elif new_status == "resolved":
        v["resolved_at"] = datetime.now().isoformat()

    v["audit_trail"].append({
        "action": f"status_changed",
        "from": old_status,
        "to": new_status,
        "by": by,
        "at": datetime.now().isoformat(),
        "note": note,
    })

    return v


def get_alerts(unread_only: bool = False, limit: int = 20) -> List[Dict]:
    """Return recent alerts."""
    alerts = _alert_queue
    if unread_only:
        alerts = [a for a in alerts if not a["read"]]
    return sorted(alerts, key=lambda a: a["created_at"], reverse=True)[:limit]


def generate_region_violations(region_id: str, region_name: str, district: str,
                                plots: List[Dict]) -> List[Dict]:
    """
    Generate realistic violations for a region's plots.
    Used for demo / seeded simulation.
    """
    rng = random.Random(hash(region_id + "_violations") % 2**32)
    violations = []

    for plot in plots:
        status = plot.get("status", "Available")
        risk = plot.get("risk_score", 0.3)

        if status == "Encroached":
            v = create_violation(
                plot_id=plot["plot_id"],
                region_id=region_id,
                violation_type="encroachment",
                severity="critical" if risk > 0.8 else "high",
                iou_score=round(rng.uniform(0.4, 0.7), 4),
                area_deviation_pct=round(rng.uniform(12, 35), 2),
                encroachment_area_sqm=round(rng.uniform(200, 2000), 1),
                risk_score=risk,
                confidence=round(rng.uniform(0.82, 0.96), 3),
                description=f"Encroachment detected beyond allotted boundary in {region_name}, Plot {plot['plot_id']}",
                snapshot_date=(datetime.now() - timedelta(days=rng.randint(1, 30))).isoformat(),
                assigned_to=f"SDM {district}",
            )
            violations.append(v)

        elif status == "Disputed":
            vtype = rng.choice(["boundary_deviation", "land_use_violation", "unauthorized_construction"])
            v = create_violation(
                plot_id=plot["plot_id"],
                region_id=region_id,
                violation_type=vtype,
                severity="high" if risk > 0.6 else "medium",
                iou_score=round(rng.uniform(0.55, 0.8), 4),
                area_deviation_pct=round(rng.uniform(5, 20), 2),
                encroachment_area_sqm=round(rng.uniform(100, 800), 1),
                risk_score=risk,
                confidence=round(rng.uniform(0.75, 0.92), 3),
                description=f"Dispute detected in {region_name}, Plot {plot['plot_id']}",
                snapshot_date=(datetime.now() - timedelta(days=rng.randint(5, 60))).isoformat(),
                assigned_to=f"Collector {district}",
            )
            violations.append(v)

        elif status == "Available" and rng.random() < 0.3:
            v = create_violation(
                plot_id=plot["plot_id"],
                region_id=region_id,
                violation_type="vacant_unused",
                severity="low",
                iou_score=0.0,
                area_deviation_pct=-100.0,
                encroachment_area_sqm=0,
                risk_score=round(rng.uniform(0.05, 0.2), 3),
                confidence=round(rng.uniform(0.88, 0.98), 3),
                description=f"Plot {plot['plot_id']} in {region_name} remains vacant",
                snapshot_date=(datetime.now() - timedelta(days=rng.randint(10, 90))).isoformat(),
            )
            violations.append(v)

        elif status == "Under Construction" and rng.random() < 0.4:
            v = create_violation(
                plot_id=plot["plot_id"],
                region_id=region_id,
                violation_type="partial_construction",
                severity="low",
                iou_score=round(rng.uniform(0.6, 0.85), 4),
                area_deviation_pct=round(rng.uniform(-30, -5), 2),
                encroachment_area_sqm=0,
                risk_score=round(rng.uniform(0.1, 0.35), 3),
                confidence=round(rng.uniform(0.8, 0.94), 3),
                description=f"Stalled construction on plot {plot['plot_id']} in {region_name}",
                snapshot_date=(datetime.now() - timedelta(days=rng.randint(15, 120))).isoformat(),
            )
            violations.append(v)

    return violations
