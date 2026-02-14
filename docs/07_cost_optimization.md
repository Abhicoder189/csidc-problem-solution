# 7️⃣ Cost Optimization Model

## 7.1 Monitoring Decision Matrix

### 7.1.1 When Satellite Is Sufficient

| Scenario | Satellite Resolution | Confidence | Action |
|----------|---------------------|------------|--------|
| New construction detected (>100 sqm) | 10m (Sentinel-2) | High | Satellite only |
| Large encroachment (>500 sqm) | 10m | Very High | Satellite only |
| Vacancy detection (entire plot) | 10m | High | Satellite only |
| Vegetation change on industrial plot | 10m | Very High | Satellite only |
| No change detected | 10m | Very High | No action needed |
| Gradual boundary expansion | 10m (multi-temporal) | Medium-High | Satellite trending |

### 7.1.2 When Drone Is Triggered

| Scenario | Why Satellite Fails | Drone Action |
|----------|-------------------|--------------|
| Encroachment 5–50 sqm | Below Sentinel-2 pixel | Targeted drone flight |
| Boundary verification (survey-grade) | ±5m accuracy insufficient | RTK drone survey |
| Legal evidence collection | 10m resolution inadmissible | High-res orthomosaic |
| AI confidence < 0.7 | Model uncertain | Visual verification |
| Construction material classification | Spectral limitation | RGB close-up |
| After legal notice — verification | Court-ready evidence needed | Timestamped drone survey |

### 7.1.3 Alert-Based Escalation Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    ESCALATION PYRAMID                            │
│                                                                  │
│                         ▲                                        │
│                        / \      Level 5: LEGAL ACTION            │
│                       / L \     Court filing, FIR                │
│                      /─────\    (₹50K per case)                  │
│                     /       \                                    │
│                    /   E     \   Level 4: FIELD INSPECTION       │
│                   /───────────\  Physical visit + drone survey   │
│                  /             \ (₹15K per site)                 │
│                 /    D          \                                 │
│                /─────────────────\ Level 3: NOTICE ISSUED        │
│               /                   \ Auto-generated legal notice  │
│              /      C              \ (₹500 per notice)           │
│             /───────────────────────\                             │
│            /                         \ Level 2: AI CONFIRMED     │
│           /        B                  \ Multi-date AI validation │
│          /─────────────────────────────\ (₹5 per analysis)      │
│         /                               \                        │
│        /           A                     \ Level 1: SATELLITE    │
│       /───────────────────────────────────\ SCREENING            │
│      /                                     \ (₹0 — free imagery)│
│     ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔                   │
│                                                                  │
│  90% resolved at Level 1-2 (near-zero cost)                    │
│  8% at Level 3 (₹500 each)                                     │
│  1.5% at Level 4 (₹15K each)                                   │
│  0.5% at Level 5 (₹50K each)                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 7.2 Estimated Cloud Cost

### 7.2.1 Compute Costs (Monthly)

| Service | Usage | Monthly Cost (₹) |
|---------|-------|-------------------|
| **Satellite Imagery** | Sentinel-2 + Landsat (free) | ₹0 |
| **Google Earth Engine** | Processing (free tier) | ₹0 |
| **AWS/Azure GPU** | 1× V100 for AI inference, ~100 hrs/mo | ₹45,000 |
| **AWS EC2 (Backend)** | 2× t3.large (24/7) | ₹18,000 |
| **RDS PostgreSQL** | db.r6g.large + PostGIS | ₹22,000 |
| **S3 Storage** | ~500 GB imagery/month | ₹800 |
| **Redis Cache** | cache.t3.medium | ₹5,000 |
| **CloudFront CDN** | Tile serving | ₹3,000 |
| **Monitoring/Logging** | CloudWatch + Grafana | ₹2,000 |
| **Total Monthly** | | **~₹95,800** |
| **Total Annual** | | **~₹11.5 Lakh** |

### 7.2.2 Drone Cost Comparison

| Metric | Drone-First Approach | ILMCS (Satellite-First) |
|--------|---------------------|------------------------|
| Annual drone flights | 112 (56 regions × 2) | ~15 (flagged plots only) |
| Cost per flight | ₹2–5 Lakh | ₹2–5 Lakh |
| Annual drone cost | ₹3.36 Cr | ₹45 Lakh |
| Cloud infrastructure | ₹0 | ₹11.5 Lakh |
| Manual inspection | ₹2 Cr | ₹20 Lakh |
| **Total Annual** | **₹5.36 Cr** | **₹76.5 Lakh** |
| **Savings** | — | **₹4.6 Cr (86%)** |

## 7.3 Batch vs Event-Driven Monitoring

### 7.3.1 Batch Processing (Default)

```
Schedule:
├── Every 5 days: Sentinel-2 ingestion + NDVI screening (all 56 regions)
├── Weekly: AI segmentation on changed tiles only
├── Bi-weekly: Full compliance assessment for flagged plots
├── Monthly: Region-level compliance report generation
└── Quarterly: Full state-wide analysis + executive report

Cost: ~₹3,200/batch cycle (compute only)
```

### 7.3.2 Event-Driven Processing (On-Demand)

```
Triggers:
├── New satellite image available (GEE notification)
│   └── Action: Cloud mask → NDVI screen → flag changes
├── Change detected above threshold
│   └── Action: Full AI segmentation on affected tiles
├── New allotment registered
│   └── Action: Baseline snapshot + boundary registration
├── Complaint received
│   └── Action: Priority analysis of specific plot
└── Legal deadline approaching
    └── Action: Generate evidence package immediately

Cost: Variable, ~₹50–500 per event depending on compute
```

### 7.3.3 Recommendation: Hybrid Approach

```
┌─────────────────────────────────────────────────────┐
│              OPTIMAL MONITORING STRATEGY             │
├─────────────────────────────────────────────────────┤
│                                                      │
│  BATCH (Scheduled):     70% of monitoring budget    │
│  ├── Sentinel-2 screening every 5 days (free)       │
│  ├── Weekly AI inference batch on GPU (₹10K/week)   │
│  └── Monthly reports (automated, ~₹1K)              │
│                                                      │
│  EVENT-DRIVEN:          30% of monitoring budget    │
│  ├── Real-time alerts for critical violations       │
│  ├── On-demand analysis for complaints              │
│  └── Priority drone trigger for legal cases         │
│                                                      │
│  Result: Continuous coverage at batch cost with      │
│  real-time responsiveness when needed                │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## 7.4 ROI Projection (5-Year)

| Year | Investment | Savings vs Status Quo | Cumulative ROI |
|------|-----------|----------------------|----------------|
| Y1 (MVP) | ₹85 Lakh (dev + infra) | ₹1.5 Cr | +₹65 Lakh |
| Y2 (Scale) | ₹45 Lakh (ops + enhance) | ₹4.2 Cr | +₹4.4 Cr |
| Y3 (Full) | ₹35 Lakh (maintenance) | ₹4.6 Cr | +₹8.7 Cr |
| Y4 | ₹30 Lakh | ₹4.6 Cr | +₹13 Cr |
| Y5 | ₹30 Lakh | ₹4.6 Cr | +₹17.3 Cr |
| **Total** | **₹2.25 Cr** | **₹19.5 Cr** | **₹17.3 Cr (769% ROI)** |
