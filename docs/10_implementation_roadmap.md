# 🔟 Implementation Roadmap

## Phase 1 — MVP (Months 1–4)

### Pilot: 3 Industrial Areas
- **SILTARA PHASE 1** (Old, large, well-documented)
- **URLA** (Old, high violation history)
- **BORAI** (Old, moderate size)

### Deliverables

| Week | Task | Deliverable |
|------|------|-------------|
| 1–2 | Requirements & data collection | Allotment maps, plot registers for 3 regions |
| 3–4 | Database setup + boundary digitization | PostGIS schema deployed, ~300 plots digitized |
| 5–6 | Satellite pipeline (GEE → storage) | Automated Sentinel-2 ingestion for 3 regions |
| 7–8 | NDVI change detection | Basic change alerts on pilot regions |
| 9–10 | Backend API (core endpoints) | Plot query, violation CRUD, basic auth |
| 11–12 | Basic dashboard (React + Leaflet) | Map view with boundary overlay + satellite WMS |
| 13–14 | Integration testing + field validation | Drone survey comparison on 20 flagged plots |
| 15–16 | Pilot report + feedback collection | Government presentation, accuracy metrics |

### Success Criteria
- [x] 100% plots digitized for 3 pilot regions
- [x] Sentinel-2 imagery displayed with boundary overlay
- [x] NDVI change detection running with >80% detection rate
- [x] Basic violation list generated
- [x] Dashboard functional for 3 regions
- [x] Drone validation: <10% false positive rate

### Budget: ₹25 Lakh
```
Breakdown:
├── Development team (4 engineers × 4 months):  ₹16 Lakh
├── Cloud infrastructure:                        ₹3 Lakh
├── Drone validation surveys (3 regions):        ₹4 Lakh
├── Boundary digitization (GIS technician):      ₹1.5 Lakh
└── Miscellaneous:                               ₹0.5 Lakh
```

---

## Phase 2 — AI Integration (Months 5–8)

### Expansion: 10 Additional Industrial Areas
Add: BHANPURI, SIRGITTI, TIFRA, RAWABHATA, TENDUA PHASE 1, TENDUA PHASE 2, SILTARA PHASE 2, ELECTRONIC EMC, TILDA, KHAPRI KHURD

### Deliverables

| Week | Task | Deliverable |
|------|------|-------------|
| 17–18 | Training data annotation (5000 tiles) | Labeled dataset for segmentation |
| 19–22 | DeepLabV3+ training + validation | Segmentation model (mIoU > 0.82) |
| 23–24 | Siamese change detection training | Change detection model (F1 > 0.85) |
| 25–26 | Encroachment classifier integration | End-to-end violation detection pipeline |
| 27–28 | IoU + risk score computation | Automated compliance scoring |
| 29–30 | PDF report generation | Legal-grade violation reports |
| 31–32 | Human review workflow | Reviewer dashboard with approve/dismiss |

### Success Criteria
- [x] AI segmentation model deployed with mIoU > 0.82
- [x] End-to-end pipeline: satellite → AI → violation → report
- [x] False positive rate < 5%
- [x] 13 regions operational
- [x] PDF reports meeting legal standards
- [x] Human review workflow functional

### Budget: ₹30 Lakh
```
Breakdown:
├── Development team (5 engineers × 4 months):  ₹20 Lakh
├── GPU compute (training):                      ₹3 Lakh
├── Data annotation (outsourced):                ₹2 Lakh
├── Cloud infrastructure:                        ₹3 Lakh
├── Drone validation (10 regions):               ₹1.5 Lakh
└── Miscellaneous:                               ₹0.5 Lakh
```

---

## Phase 3 — Full Automation (Months 9–14)

### Expansion: All 56 Industrial Areas

### Deliverables

| Month | Task | Deliverable |
|-------|------|-------------|
| 9 | Digitize remaining 43 regions | All 56 regions in PostGIS |
| 10 | Deploy batch processing pipeline | Celery-based parallel processing |
| 11 | Automated alert system | SMS/Email alerts for critical violations |
| 12 | Executive dashboard | State-wide compliance overview |
| 13 | Payment integration | Cross-verify land-use with payment status |
| 14 | Predictive analytics | Encroachment trend forecasting |

### Advanced Features

| Feature | Description |
|---------|-------------|
| Predictive encroachment | ML forecasting of plots likely to violate in next 6 months |
| Industry activity classification | Running / Closed / Under Construction from satellite |
| Encroachment trend analytics | Time-series analysis of boundary violations |
| Payment cross-verification | Flag plots with overdue payments + violations |
| Automated legal notices | Template-based notice generation with evidence |

### Success Criteria
- [x] All 56 regions operational
- [x] Fully automated monitoring pipeline (no manual trigger)
- [x] Alert system delivering within 48 hours of detection
- [x] Executive dashboard used by senior officials
- [x] Predictive model with >70% accuracy at 6-month forecast

### Budget: ₹20 Lakh
```
Breakdown:
├── Development team (3 engineers × 6 months):  ₹12 Lakh
├── Digitization (43 regions):                   ₹3 Lakh
├── Cloud infrastructure scale-up:               ₹4 Lakh
└── Training & documentation:                    ₹1 Lakh
```

---

## Phase 4 — Statewide Rollout & Governance (Months 15–18)

### Deliverables

| Month | Task | Deliverable |
|-------|------|-------------|
| 15 | Government training program | 50+ trained users across departments |
| 16 | Integration with CSIDC portal | SSO, data sharing, API federation |
| 17 | Performance optimization | Sub-second map loading, optimized queries |
| 18 | Audit + security + compliance certification | Government IT security approval |

### Governance Integration

```
ILMCS ←→ CSIDC Portal:
├── Plot allotment records sync (bi-directional)
├── Payment status from treasury system
├── Violation notices to legal department
├── Compliance reports to CM dashboard
└── RTI data export API

Authentication: State SSO (Aadhaar-linked / department ID)
```

### Budget: ₹10 Lakh
```
Breakdown:
├── Development (optimization + integration):  ₹5 Lakh
├── Training programs:                          ₹2 Lakh
├── Security audit:                             ₹2 Lakh
└── Documentation + handover:                   ₹1 Lakh
```

---

## Total Budget Summary

| Phase | Duration | Budget | Regions |
|-------|----------|--------|---------|
| Phase 1 — MVP | 4 months | ₹25 Lakh | 3 |
| Phase 2 — AI | 4 months | ₹30 Lakh | 13 |
| Phase 3 — Automation | 6 months | ₹20 Lakh | 56 |
| Phase 4 — Rollout | 4 months | ₹10 Lakh | 56 (production) |
| **Total** | **18 months** | **₹85 Lakh** | **56 regions** |

---

# 🎖️ Competitive Edge Features

## Advanced Innovations

### 1. Predictive Encroachment Forecasting

```python
from sklearn.ensemble import GradientBoostingClassifier

features = [
    'months_since_allotment',
    'distance_to_road_m',
    'adjacent_plot_violation_count',
    'plot_area_sqm',
    'vacancy_duration_months',
    'payment_overdue_count',
    'region_violation_density',
    'boundary_complexity',  # perimeter/area ratio
]

# Train on historical violation data
model = GradientBoostingClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.1
)
model.fit(X_train[features], y_train)

# Predict probability of violation in next 6 months
risk_probabilities = model.predict_proba(X_current[features])[:, 1]
```

### 2. Industry Activity Classification

```
Satellite indicators for industrial activity status:

RUNNING (Active):
├── Thermal anomaly (Sentinel-3 SLSTR or Landsat thermal)
├── Vehicle/container detection on premises
├── Smoke/emission plume detection
└── Consistent NDBI signature

CLOSED (Inactive):
├── No thermal anomaly over 6+ months
├── Increasing vegetation encroachment
├── No vehicular activity in parking areas
└── Deteriorating roof/structure in change detection

UNDER CONSTRUCTION:
├── Increasing NDBI over consecutive passes
├── Bare soil to built-up transition
├── Changing building footprint geometry
└── Construction material spectral signature
```

### 3. Risk-Based Compliance Scoring

```
Compliance Grade = f(boundary, utilization, payment, history)

Grade A (90–100): Exemplary compliance → Reduced monitoring frequency
Grade B (75–89):  Good compliance     → Standard monitoring
Grade C (60–74):  Fair compliance     → Increased monitoring
Grade D (40–59):  Poor compliance     → Active investigation
Grade F (0–39):   Non-compliant       → Enforcement action

Incentive: Grade A plots get 5-year lease renewal fast-tracked
Penalty:   Grade F plots flagged for lease cancellation review
```

### 4. Encroachment Trend Analytics

```
For each plot, compute temporal encroachment trajectory:

E(t) = encroachment_area at time t

Metrics:
├── Trend: Linear regression slope of E(t)
│   → Positive slope = growing encroachment (high risk)
│   → Negative slope = encroachment receding (corrective action taken)
│   → Zero slope = stable (monitoring sufficient)
│
├── Velocity: ΔE / Δt (sqm per month)
│   → > 10 sqm/month = rapid encroachment alert
│
└── Acceleration: Δ²E / Δt² (change in velocity)
    → Positive acceleration = encroachment accelerating (urgent)
```

### 5. Payment + Land-Use Cross-Verification

```sql
-- Flag plots with BOTH payment issues AND violations
SELECT 
    p.plot_id,
    p.plot_number,
    p.allottee_name,
    cs.overall_score AS compliance_score,
    ps.total_overdue,
    v.active_violation_count,
    CASE 
        WHEN cs.overall_score < 50 AND ps.total_overdue > 100000 THEN 'CRITICAL_DUAL'
        WHEN cs.overall_score < 70 AND ps.total_overdue > 50000 THEN 'HIGH_DUAL'
        WHEN cs.overall_score < 70 OR ps.total_overdue > 50000 THEN 'MODERATE'
        ELSE 'OK'
    END AS cross_risk_category
FROM plot p
JOIN compliance_status cs ON p.plot_id = cs.plot_id
JOIN (
    SELECT plot_id, SUM(amount_inr) AS total_overdue
    FROM payment_status
    WHERE status = 'OVERDUE'
    GROUP BY plot_id
) ps ON p.plot_id = ps.plot_id
JOIN (
    SELECT plot_id, COUNT(*) AS active_violation_count
    FROM violation
    WHERE status NOT IN ('RESOLVED', 'DISMISSED')
    GROUP BY plot_id
) v ON p.plot_id = v.plot_id
ORDER BY cross_risk_category, cs.overall_score ASC;
```
