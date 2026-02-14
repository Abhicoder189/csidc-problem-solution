# 6️⃣ Dashboard Design

## 6.1 Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏭 ILMCS — Industrial Land Monitoring & Compliance System             │
│  ┌──────┐ ┌──────────┐ ┌────────────┐ ┌──────────────┐ ┌───────────┐  │
│  │ Home │ │ Regions  │ │ Violations │ │ Compliance   │ │ Reports   │  │
│  └──────┘ └──────────┘ └────────────┘ └──────────────┘ └───────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─── SUMMARY CARDS ──────────────────────────────────────────────────┐ │
│  │ 📊 56 Regions  │ 📦 12,450 Plots │ ⚠️ 342 Violations │ ✅ 87% OK │ │
│  └────────────────┴─────────────────┴───────────────────┴────────────┘ │
│                                                                         │
│  ┌─── LEFT: INTERACTIVE MAP ──────────┐ ┌─── RIGHT: PANELS ─────────┐ │
│  │                                     │ │                            │ │
│  │  ╔══════════════════════════════╗   │ │ ┌── REGION SELECTOR ────┐ │ │
│  │  ║                              ║   │ │ │ [▾ Select Region    ] │ │ │
│  │  ║   Chhattisgarh Map          ║   │ │ │   SILTARA PHASE 1    │ │ │
│  │  ║                              ║   │ │ │   URLA               │ │ │
│  │  ║    🔴 ⚠️                     ║   │ │ │   BORAI              │ │ │
│  │  ║       🟢 🟢                  ║   │ │ └──────────────────────┘ │ │
│  │  ║    🟡    🟢                  ║   │ │                            │ │
│  │  ║  🟠  🔴   🟢                ║   │ │ ┌── RISK FILTER ────────┐ │ │
│  │  ║       🟢    🟡              ║   │ │ │ [x] Critical (34)     │ │ │
│  │  ║                              ║   │ │ │ [x] High (67)        │ │ │
│  │  ║   [🔍 Zoom] [📍Locate]      ║   │ │ │ [x] Medium (89)      │ │ │
│  │  ╚══════════════════════════════╝   │ │ │ [ ] Low (152)        │ │ │
│  │                                     │ │ └──────────────────────┘ │ │
│  │  ┌── LAYER CONTROLS ─────────────┐ │ │                            │ │
│  │  │ [x] Plot Boundaries           │ │ │ ┌── COMPLIANCE CHART ───┐ │ │
│  │  │ [x] Satellite Overlay         │ │ │ │ ████████ 87% Compliant│ │ │
│  │  │ [x] Violation Heatmap         │ │ │ │ ███░░░░░ 8% Minor     │ │ │
│  │  │ [ ] NDVI Layer                │ │ │ │ ██░░░░░░ 3% Critical  │ │ │
│  │  │ [ ] Change Detection          │ │ │ │ █░░░░░░░ 2% Severe    │ │ │
│  │  └────────────────────────────────┘ │ │ └──────────────────────┘ │ │
│  └─────────────────────────────────────┘ └────────────────────────────┘ │
│                                                                         │
│  ┌─── TIME SLIDER ──────────────────────────────────────────────────────┐
│  │ ◄ 2024-01  ●────────────────────────●──────────► 2026-02             │
│  │            T1                       T2           [Compare] [Animate] │
│  └──────────────────────────────────────────────────────────────────────┘
│                                                                         │
│  ┌─── PLOT DETAIL PANEL (on click) ─────────────────────────────────────┐
│  │ Plot: SIL-P-0234 | Owner: M/s XYZ Industries | Area: 2,450 sqm      │
│  │ IoU: 0.82 | Deviation: +12.3% | Risk: HIGH (0.67)                   │
│  │ [View Satellite] [View Overlay] [Download Report] [Flag for Review]  │
│  └──────────────────────────────────────────────────────────────────────┘
│                                                                         │
│  ┌─── VIOLATION TABLE ──────────────────────────────────────────────────┐
│  │ ID      │ Plot     │ Type         │ Severity │ Area(sqm)│ Status    │
│  │ V-00342 │ SIL-0234 │ ENCROACHMENT │ HIGH     │ 302.5   │ DETECTED  │
│  │ V-00341 │ URL-0089 │ VACANCY      │ MEDIUM   │ 1200.0  │ CONFIRMED │
│  │ V-00340 │ BOR-0012 │ BOUNDARY     │ CRITICAL │ 456.8   │ ESCALATED │
│  │ ...     │          │              │          │         │           │
│  │                    [Export CSV] [Export PDF] [1 2 3 ... 12 ▸]        │
│  └──────────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────────┘
```

## 6.2 Dashboard Components Specification

### 6.2.1 Region Heatmap

| Feature | Implementation |
|---------|---------------|
| Base Map | OpenStreetMap / Mapbox (govt-approved tiles) |
| Heatmap Layer | `react-leaflet-heatmap-layer` using violation density |
| Color Scale | Green (0 violations) → Red (10+ violations per plot) |
| Interaction | Click region → zoom to industrial area |
| Data Source | `GET /api/v1/dashboard/heatmap` → GeoJSON FeatureCollection |

### 6.2.2 Plot-Level Violation Overlay

```javascript
// Color-coded polygon rendering based on compliance
const getPlotStyle = (complianceScore) => ({
  fillColor: complianceScore > 80 ? '#22c55e' :    // Green (compliant)
             complianceScore > 60 ? '#eab308' :    // Yellow (minor)  
             complianceScore > 40 ? '#f97316' :    // Orange (moderate)
             complianceScore > 20 ? '#ef4444' :    // Red (critical)
                                    '#1f2937',      // Black (severe)
  weight: 2,
  opacity: 0.8,
  fillOpacity: 0.4,
});

// Encroachment polygon overlay (red hatched)
const encroachmentStyle = {
  fillColor: '#dc2626',
  fillPattern: 'crosshatch',  // Custom SVG pattern
  weight: 3,
  color: '#991b1b',
  dashArray: '5,5',
  fillOpacity: 0.6,
};
```

### 6.2.3 Time Slider Comparison

| Feature | Detail |
|---------|--------|
| Range | Earliest snapshot → Latest snapshot per region |
| Granularity | Per satellite pass (~5-day intervals) |
| Mode 1 — Swipe | Left/right curtain comparing T1 vs T2 imagery |
| Mode 2 — Flicker | Rapid toggle between T1 and T2 |
| Mode 3 — Side-by-Side | Split screen comparison |
| Mode 4 — Animation | Auto-play through all snapshots chronologically |

### 6.2.4 Risk-Based Filtering

```
Filter Dimensions:
├── Severity: Critical / High / Medium / Low
├── Violation Type: Encroachment / Vacancy / Boundary / Land-Use
├── Region: Dropdown with all 56 regions
├── Date Range: Custom date picker
├── Compliance Score: Slider 0–100
├── Payment Status: Paid / Overdue / Pending
└── Review Status: Detected / Confirmed / Resolved / Dismissed
```

### 6.2.5 Compliance Scoring Dashboard

```
Overall Compliance Score (Region Level):

Score = Σ(plot_compliance_score × plot_area) / Σ(plot_area)

Weighted by plot area to reflect actual land impact.

Visual: Gauge chart (0–100) with color zones
  0–30:  Red zone
  30–60: Yellow zone
  60–80: Blue zone
  80–100: Green zone
```

### 6.2.6 PDF Report Export

| Report Type | Content | Trigger |
|-------------|---------|---------|
| Plot Compliance Report | Single plot analysis with maps + metrics | On-demand per plot |
| Region Summary | All plots in a region, aggregated stats | Monthly auto-generate |
| Violation Detail | Full evidence package for legal action | Per confirmed violation |
| Executive Dashboard | State-wide summary for CM/Secretary | Quarterly auto-generate |
| Audit Report | System activity log + actions taken | On-demand |

```
PDF Generation Pipeline:
1. Backend: FastAPI endpoint collects data + renders Jinja2 HTML template
2. Generates map images via headless Leaflet (Puppeteer)
3. Converts HTML → PDF using WeasyPrint
4. Embeds GIS overlays as inline images
5. Adds digital timestamp and report hash for authenticity
6. Stores in MinIO/S3 with versioning
```
