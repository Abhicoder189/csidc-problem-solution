# 5️⃣ Database Schema (Detailed)

## 5.1 Entity-Relationship Diagram

```
┌──────────────────┐       ┌───────────────────┐
│ IndustrialRegion │       │   SatelliteSnapshot│
│──────────────────│       │───────────────────│
│ PK region_id     │       │ PK snapshot_id     │
│    name           │       │ FK region_id       │
│    type (new/old) │       │    source          │
│    state          │◄──────│    captured_at     │
│    district       │  1:N  │    cloud_cover_pct │
│    boundary_geom  │       │    resolution_m    │
│    total_area_sqm │       │    raster_path     │
│    created_at     │       │    processed       │
└────────┬─────────┘       └────────┬──────────┘
         │ 1:N                      │
         ▼                          │
┌──────────────────┐                │
│      Plot        │                │
│──────────────────│                │
│ PK plot_id       │                │
│ FK region_id     │                │
│    plot_number   │                │
│    allottee_name │                │
│    allotment_date│                │
│    lease_years   │                │
│    purpose       │                │
│    status        │                │
└────────┬─────────┘                │
         │ 1:1                      │
         ▼                          │
┌──────────────────┐                │
│AllotmentBoundary │                │
│──────────────────│                │
│ PK boundary_id   │                │
│ FK plot_id       │                │
│    geom (POLYGON)│                │
│    area_sqm      │                │
│    source_type   │                │
│    digitized_at  │                │
│    accuracy_m    │                │
│    verified      │                │
└────────┬─────────┘                │
         │                          │
         │ 1:N                      │
         ▼                          │
┌──────────────────┐       ┌───────┴───────────┐
│    Violation     │       │ DetectedStructure  │
│──────────────────│       │───────────────────│
│ PK violation_id  │       │ PK structure_id    │
│ FK plot_id       │◄──────│ FK plot_id         │
│ FK snapshot_id   │       │ FK snapshot_id     │
│ FK structure_id  │       │    geom (POLYGON)  │
│    type          │       │    area_sqm        │
│    severity      │       │    class_label     │
│    encroach_geom │       │    confidence      │
│    encroach_sqm  │       │    detected_at     │
│    iou_score     │       └───────────────────┘
│    deviation_pct │
│    risk_score    │
│    status        │
│    detected_at   │
│    resolved_at   │
└────────┬─────────┘
         │ 1:1
         ▼
┌──────────────────┐       ┌──────────────────┐
│ComplianceStatus  │       │  PaymentStatus   │
│──────────────────│       │──────────────────│
│ PK compliance_id │       │ PK payment_id    │
│ FK plot_id       │       │ FK plot_id       │
│    score (0–100) │       │    amount        │
│    category      │       │    due_date      │
│    last_assessed │       │    paid_date     │
│    next_review   │       │    status        │
│    assessor      │       │    receipt_no    │
│    notes         │       │    fiscal_year   │
└──────────────────┘       └──────────────────┘
```

---

## 5.2 Complete SQL Schema

```sql
-- ============================================================
-- ILMCS Database Schema - PostGIS
-- Target: PostgreSQL 15+ with PostGIS 3.4+
-- SRID: 4326 (storage) / 32644 (computation)
-- ============================================================

-- Enable PostGIS extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- For text search

-- ============================================================
-- TABLE: industrial_region
-- ============================================================
CREATE TABLE industrial_region (
    region_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(50) UNIQUE NOT NULL,
    type            VARCHAR(10) NOT NULL CHECK (type IN ('NEW', 'OLD')),
    state           VARCHAR(100) NOT NULL DEFAULT 'Chhattisgarh',
    district        VARCHAR(100),
    tehsil          VARCHAR(100),
    boundary_geom   GEOMETRY(MultiPolygon, 4326) NOT NULL,
    total_area_sqm  FLOAT GENERATED ALWAYS AS (
                        ST_Area(ST_Transform(boundary_geom, 32644))
                    ) STORED,
    total_plots     INTEGER DEFAULT 0,
    centroid_lat    FLOAT,
    centroid_lon    FLOAT,
    established_date DATE,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: plot
-- ============================================================
CREATE TABLE plot (
    plot_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_id       UUID NOT NULL REFERENCES industrial_region(region_id)
                        ON DELETE CASCADE,
    plot_number     VARCHAR(50) NOT NULL,
    allottee_name   VARCHAR(300),
    allottee_entity VARCHAR(300),
    allotment_date  DATE,
    lease_type      VARCHAR(50) CHECK (lease_type IN (
                        'FREEHOLD', 'LEASEHOLD_30', 'LEASEHOLD_60', 'LEASEHOLD_90'
                    )),
    lease_years     INTEGER,
    lease_expiry    DATE,
    approved_purpose VARCHAR(200),
    approved_activity VARCHAR(200),
    plot_status     VARCHAR(30) DEFAULT 'ALLOTTED' CHECK (plot_status IN (
                        'ALLOTTED', 'ACTIVE', 'VACANT', 'UNDER_CONSTRUCTION',
                        'DISPUTED', 'SURRENDERED', 'CANCELLED'
                    )),
    contact_phone   VARCHAR(20),
    contact_email   VARCHAR(200),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(region_id, plot_number)
);

-- ============================================================
-- TABLE: allotment_boundary
-- ============================================================
CREATE TABLE allotment_boundary (
    boundary_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id         UUID NOT NULL REFERENCES plot(plot_id)
                        ON DELETE CASCADE,
    geom            GEOMETRY(Polygon, 4326) NOT NULL,
    area_sqm        FLOAT GENERATED ALWAYS AS (
                        ST_Area(ST_Transform(geom, 32644))
                    ) STORED,
    perimeter_m     FLOAT GENERATED ALWAYS AS (
                        ST_Perimeter(ST_Transform(geom, 32644))
                    ) STORED,
    source_type     VARCHAR(30) NOT NULL CHECK (source_type IN (
                        'SHAPEFILE', 'GEOJSON', 'CAD', 'PDF_VECTORIZED',
                        'SURVEY_GPS', 'MANUAL_DIGITIZATION'
                    )),
    source_file     VARCHAR(500),
    coordinate_system VARCHAR(50) DEFAULT 'EPSG:4326',
    accuracy_m      FLOAT DEFAULT 5.0,
    digitized_by    VARCHAR(200),
    digitized_at    TIMESTAMPTZ DEFAULT NOW(),
    verified        BOOLEAN DEFAULT FALSE,
    verified_by     VARCHAR(200),
    verified_at     TIMESTAMPTZ,
    version         INTEGER DEFAULT 1,
    is_active       BOOLEAN DEFAULT TRUE,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: satellite_snapshot
-- Partitioned by captured_at for time-series performance
-- ============================================================
CREATE TABLE satellite_snapshot (
    snapshot_id     UUID NOT NULL DEFAULT gen_random_uuid(),
    region_id       UUID NOT NULL REFERENCES industrial_region(region_id),
    source          VARCHAR(30) NOT NULL CHECK (source IN (
                        'SENTINEL2', 'LANDSAT8', 'LANDSAT9', 'SENTINEL1',
                        'PLANET', 'DRONE', 'GOOGLE_EARTH'
                    )),
    captured_at     DATE NOT NULL,
    cloud_cover_pct FLOAT DEFAULT 0,
    resolution_m    FLOAT NOT NULL,
    bands           TEXT[],
    footprint_geom  GEOMETRY(Polygon, 4326),
    raster_path     VARCHAR(500) NOT NULL,
    thumbnail_path  VARCHAR(500),
    file_size_mb    FLOAT,
    processing_level VARCHAR(10) DEFAULT 'L2A',
    is_processed    BOOLEAN DEFAULT FALSE,
    processing_log  JSONB DEFAULT '{}',
    ndvi_computed   BOOLEAN DEFAULT FALSE,
    segmentation_done BOOLEAN DEFAULT FALSE,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (snapshot_id, captured_at)
) PARTITION BY RANGE (captured_at);

-- Create yearly partitions
CREATE TABLE satellite_snapshot_2024 PARTITION OF satellite_snapshot
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE satellite_snapshot_2025 PARTITION OF satellite_snapshot
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE satellite_snapshot_2026 PARTITION OF satellite_snapshot
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE satellite_snapshot_2027 PARTITION OF satellite_snapshot
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');

-- ============================================================
-- TABLE: detected_structure
-- AI-detected building footprints from satellite imagery
-- ============================================================
CREATE TABLE detected_structure (
    structure_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id         UUID REFERENCES plot(plot_id),
    snapshot_id     UUID NOT NULL,
    snapshot_date   DATE NOT NULL,  -- For partition reference
    geom            GEOMETRY(Polygon, 4326) NOT NULL,
    area_sqm        FLOAT GENERATED ALWAYS AS (
                        ST_Area(ST_Transform(geom, 32644))
                    ) STORED,
    class_label     VARCHAR(50) NOT NULL CHECK (class_label IN (
                        'BUILT_UP', 'PAVED', 'VACANT', 'VEGETATION',
                        'WATER', 'INDUSTRIAL_ACTIVE', 'UNDER_CONSTRUCTION'
                    )),
    confidence      FLOAT CHECK (confidence BETWEEN 0 AND 1),
    model_version   VARCHAR(50),
    detected_at     TIMESTAMPTZ DEFAULT NOW(),
    
    FOREIGN KEY (snapshot_id, snapshot_date)
        REFERENCES satellite_snapshot(snapshot_id, captured_at)
);

-- ============================================================
-- TABLE: violation
-- ============================================================
CREATE TABLE violation (
    violation_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id         UUID NOT NULL REFERENCES plot(plot_id),
    snapshot_id     UUID NOT NULL,
    snapshot_date   DATE NOT NULL,
    structure_id    UUID REFERENCES detected_structure(structure_id),
    
    violation_type  VARCHAR(50) NOT NULL CHECK (violation_type IN (
                        'ENCROACHMENT', 'BOUNDARY_EXCEED', 'VACANCY',
                        'LAND_USE_CHANGE', 'UNAUTHORIZED_CONSTRUCTION',
                        'BOUNDARY_SHIFT', 'PARTIAL_UTILIZATION'
                    )),
    severity        VARCHAR(20) NOT NULL CHECK (severity IN (
                        'LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'SEVERE'
                    )),
    
    -- Quantitative metrics
    encroachment_geom   GEOMETRY(Polygon, 4326),
    encroachment_area_sqm FLOAT DEFAULT 0,
    iou_score           FLOAT CHECK (iou_score BETWEEN 0 AND 1),
    area_deviation_pct  FLOAT,
    risk_score          FLOAT CHECK (risk_score BETWEEN 0 AND 1),
    confidence_score    FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    
    -- Evidence
    evidence_image_path VARCHAR(500),
    overlay_image_path  VARCHAR(500),
    
    -- Status tracking
    status          VARCHAR(30) DEFAULT 'DETECTED' CHECK (status IN (
                        'DETECTED', 'CONFIRMED', 'UNDER_REVIEW',
                        'NOTICE_ISSUED', 'RESOLVED', 'DISMISSED',
                        'ESCALATED', 'LEGAL_ACTION'
                    )),
    
    -- Timestamps
    detected_at     TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at    TIMESTAMPTZ,
    notice_sent_at  TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    
    -- Review
    reviewed_by     VARCHAR(200),
    review_notes    TEXT,
    
    -- Audit
    auto_detected   BOOLEAN DEFAULT TRUE,
    false_positive  BOOLEAN DEFAULT FALSE,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    FOREIGN KEY (snapshot_id, snapshot_date)
        REFERENCES satellite_snapshot(snapshot_id, captured_at)
);

-- ============================================================
-- TABLE: compliance_status
-- ============================================================
CREATE TABLE compliance_status (
    compliance_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id         UUID NOT NULL REFERENCES plot(plot_id),
    
    -- Scoring
    overall_score   FLOAT CHECK (overall_score BETWEEN 0 AND 100),
    boundary_score  FLOAT CHECK (boundary_score BETWEEN 0 AND 100),
    utilization_score FLOAT CHECK (utilization_score BETWEEN 0 AND 100),
    payment_score   FLOAT CHECK (payment_score BETWEEN 0 AND 100),
    
    category        VARCHAR(20) CHECK (category IN (
                        'COMPLIANT', 'MINOR_ISSUES', 'NON_COMPLIANT',
                        'CRITICAL', 'UNASSESSED'
                    )),
    
    active_violations INTEGER DEFAULT 0,
    total_violations  INTEGER DEFAULT 0,
    
    last_assessed_at  TIMESTAMPTZ,
    next_review_at    TIMESTAMPTZ,
    assessed_by       VARCHAR(200) DEFAULT 'SYSTEM_AUTO',
    assessment_notes  TEXT,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(plot_id)
);

-- ============================================================
-- TABLE: payment_status
-- ============================================================
CREATE TABLE payment_status (
    payment_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id         UUID NOT NULL REFERENCES plot(plot_id),
    
    payment_type    VARCHAR(50) CHECK (payment_type IN (
                        'LEASE_RENT', 'MAINTENANCE_FEE', 'PENALTY',
                        'ONE_TIME_PREMIUM', 'CONVERSION_FEE'
                    )),
    amount_inr      NUMERIC(15,2) NOT NULL,
    due_date        DATE NOT NULL,
    paid_date       DATE,
    status          VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN (
                        'PENDING', 'PAID', 'OVERDUE', 'PARTIAL', 'WAIVED'
                    )),
    receipt_number  VARCHAR(100),
    transaction_ref VARCHAR(200),
    fiscal_year     VARCHAR(10) NOT NULL,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: audit_log
-- Immutable event log for all system actions
-- ============================================================
CREATE TABLE audit_log (
    log_id          BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       UUID NOT NULL,
    action          VARCHAR(50) NOT NULL,
    actor           VARCHAR(200) NOT NULL,
    actor_role      VARCHAR(50),
    details         JSONB DEFAULT '{}',
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE: analysis_job
-- Track async processing jobs
-- ============================================================
CREATE TABLE analysis_job (
    job_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_id       UUID REFERENCES industrial_region(region_id),
    job_type        VARCHAR(50) NOT NULL CHECK (job_type IN (
                        'SATELLITE_INGEST', 'SEGMENTATION',
                        'CHANGE_DETECTION', 'COMPLIANCE_CHECK',
                        'REPORT_GENERATION', 'FULL_ANALYSIS'
                    )),
    status          VARCHAR(20) DEFAULT 'QUEUED' CHECK (status IN (
                        'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'
                    )),
    progress_pct    FLOAT DEFAULT 0,
    parameters      JSONB DEFAULT '{}',
    result          JSONB DEFAULT '{}',
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5.3 Spatial Indexing Strategy

```sql
-- ============================================================
-- SPATIAL INDEXES (GiST)
-- ============================================================

-- Region boundary - for region lookups by location
CREATE INDEX idx_region_boundary_geom
    ON industrial_region USING GIST (boundary_geom);

-- Allotment boundary - most queried spatial column
CREATE INDEX idx_allotment_boundary_geom
    ON allotment_boundary USING GIST (geom);

-- Detected structures - for overlay analysis
CREATE INDEX idx_detected_structure_geom
    ON detected_structure USING GIST (geom);

-- Violation encroachment - for violation mapping
CREATE INDEX idx_violation_encroachment_geom
    ON violation USING GIST (encroachment_geom);

-- Satellite footprint - for coverage queries
CREATE INDEX idx_snapshot_footprint_geom
    ON satellite_snapshot USING GIST (footprint_geom);

-- ============================================================
-- B-TREE INDEXES (Standard lookups)
-- ============================================================

CREATE INDEX idx_plot_region ON plot(region_id);
CREATE INDEX idx_plot_status ON plot(plot_status);
CREATE INDEX idx_plot_number ON plot(plot_number);
CREATE INDEX idx_boundary_plot ON allotment_boundary(plot_id);
CREATE INDEX idx_boundary_active ON allotment_boundary(is_active);
CREATE INDEX idx_snapshot_region ON satellite_snapshot(region_id);
CREATE INDEX idx_snapshot_source ON satellite_snapshot(source);
CREATE INDEX idx_detected_plot ON detected_structure(plot_id);
CREATE INDEX idx_detected_class ON detected_structure(class_label);
CREATE INDEX idx_violation_plot ON violation(plot_id);
CREATE INDEX idx_violation_type ON violation(violation_type);
CREATE INDEX idx_violation_status ON violation(status);
CREATE INDEX idx_violation_severity ON violation(severity);
CREATE INDEX idx_compliance_plot ON compliance_status(plot_id);
CREATE INDEX idx_compliance_category ON compliance_status(category);
CREATE INDEX idx_payment_plot ON payment_status(plot_id);
CREATE INDEX idx_payment_status ON payment_status(status);
CREATE INDEX idx_payment_fiscal ON payment_status(fiscal_year);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);

-- ============================================================
-- COMPOSITE INDEXES (Query optimization)
-- ============================================================

CREATE INDEX idx_violation_plot_status
    ON violation(plot_id, status, detected_at DESC);

CREATE INDEX idx_snapshot_region_date
    ON satellite_snapshot(region_id, captured_at DESC);

CREATE INDEX idx_detected_snapshot_class
    ON detected_structure(snapshot_id, class_label);
```

---

## 5.4 Partitioning Strategy

```
Table                    │ Strategy         │ Partition Key    │ Rationale
─────────────────────────┼──────────────────┼──────────────────┼──────────────────────
satellite_snapshot       │ RANGE by year    │ captured_at      │ ~70 images/region/yr
detected_structure       │ RANGE by year    │ snapshot_date    │ Linked to snapshots
violation                │ RANGE by year    │ snapshot_date    │ Growing over time
audit_log                │ RANGE by month   │ created_at       │ High-volume writes
industrial_region        │ None             │ —                │ Only 56 rows
plot                     │ LIST by region   │ region_id        │ Regional parallelism
allotment_boundary       │ None             │ —                │ Relatively static
compliance_status        │ None             │ —                │ 1:1 with plot
payment_status           │ RANGE by year    │ due_date         │ Fiscal year queries
```
