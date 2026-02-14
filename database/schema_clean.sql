-- ═══════════════════════════════════════════════════════════════════
-- ILMCS Database Schema — Aligned with SQLAlchemy ORM Models
-- Industrial Land Monitoring & Compliance System
-- Chhattisgarh — 56 Industrial Regions (36 New + 20 Old)
-- ═══════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: industrial_region
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS industrial_region (
    region_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(50) NOT NULL UNIQUE,
    type            VARCHAR(10) NOT NULL CHECK (type IN ('NEW', 'OLD')),
    state           VARCHAR(100) DEFAULT 'Chhattisgarh',
    district        VARCHAR(100),
    tehsil          VARCHAR(100),
    boundary_geom   GEOMETRY(MultiPolygon, 4326),
    total_plots     INTEGER DEFAULT 0,
    centroid_lat    DOUBLE PRECISION,
    centroid_lon    DOUBLE PRECISION,
    established_date DATE,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_region_boundary ON industrial_region USING GIST (boundary_geom);
CREATE INDEX IF NOT EXISTS idx_region_type ON industrial_region (type);
CREATE INDEX IF NOT EXISTS idx_region_district ON industrial_region (district);
CREATE INDEX IF NOT EXISTS idx_region_name_trgm ON industrial_region USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_region_code ON industrial_region (code);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: plot
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS plot (
    plot_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_id       UUID NOT NULL REFERENCES industrial_region(region_id) ON DELETE CASCADE,
    plot_number     VARCHAR(50) NOT NULL,
    allottee_name   VARCHAR(300),
    allottee_entity VARCHAR(300),
    allotment_date  DATE,
    lease_type      VARCHAR(50),
    lease_years     INTEGER,
    lease_expiry    DATE,
    approved_purpose VARCHAR(200),
    approved_activity VARCHAR(200),
    plot_status     VARCHAR(30) DEFAULT 'ALLOTTED',
    contact_phone   VARCHAR(20),
    contact_email   VARCHAR(200),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_plot_per_region UNIQUE(region_id, plot_number)
);

CREATE INDEX IF NOT EXISTS idx_plot_region ON plot (region_id);
CREATE INDEX IF NOT EXISTS idx_plot_status ON plot (plot_status);
CREATE INDEX IF NOT EXISTS idx_plot_number ON plot (plot_number);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: allotment_boundary
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS allotment_boundary (
    boundary_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id         UUID NOT NULL REFERENCES plot(plot_id) ON DELETE CASCADE,
    geom            GEOMETRY(Polygon, 4326) NOT NULL,
    source_type     VARCHAR(30) NOT NULL,
    source_file     VARCHAR(500),
    accuracy_m      DOUBLE PRECISION DEFAULT 5.0,
    digitized_by    VARCHAR(200),
    digitized_at    TIMESTAMPTZ DEFAULT NOW(),
    verified        BOOLEAN DEFAULT FALSE,
    verified_by     VARCHAR(200),
    verified_at     TIMESTAMPTZ,
    version         INTEGER DEFAULT 1,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_allotment_boundary_geom ON allotment_boundary USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_allotment_boundary_plot ON allotment_boundary (plot_id);
CREATE INDEX IF NOT EXISTS idx_allotment_boundary_active ON allotment_boundary (plot_id, is_active) WHERE is_active = TRUE;

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: satellite_snapshot
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS satellite_snapshot (
    snapshot_id     UUID DEFAULT gen_random_uuid(),
    region_id       UUID NOT NULL REFERENCES industrial_region(region_id),
    source          VARCHAR(30) NOT NULL,
    captured_at     DATE NOT NULL,
    cloud_cover_pct DOUBLE PRECISION DEFAULT 0,
    resolution_m    DOUBLE PRECISION NOT NULL,
    bands           TEXT[],
    footprint_geom  GEOMETRY(Polygon, 4326),
    raster_path     VARCHAR(500) NOT NULL,
    thumbnail_path  VARCHAR(500),
    file_size_mb    DOUBLE PRECISION,
    processing_level VARCHAR(10) DEFAULT 'L2A',
    is_processed    BOOLEAN DEFAULT FALSE,
    ndvi_computed   BOOLEAN DEFAULT FALSE,
    segmentation_done BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (snapshot_id, captured_at)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_region ON satellite_snapshot (region_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_date ON satellite_snapshot (captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_snapshot_geom ON satellite_snapshot USING GIST (footprint_geom);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: violation
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS violation (
    violation_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id         UUID NOT NULL REFERENCES plot(plot_id),
    snapshot_id     UUID NOT NULL,
    snapshot_date   DATE NOT NULL,
    structure_id    UUID,
    violation_type  VARCHAR(50) NOT NULL,
    severity        VARCHAR(20) NOT NULL,
    encroachment_geom GEOMETRY(Polygon, 4326),
    encroachment_area_sqm DOUBLE PRECISION DEFAULT 0,
    iou_score       DOUBLE PRECISION,
    area_deviation_pct DOUBLE PRECISION,
    risk_score      DOUBLE PRECISION,
    confidence_score DOUBLE PRECISION,
    evidence_image_path VARCHAR(500),
    overlay_image_path VARCHAR(500),
    status          VARCHAR(30) DEFAULT 'DETECTED',
    detected_at     TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at    TIMESTAMPTZ,
    notice_sent_at  TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    reviewed_by     VARCHAR(200),
    review_notes    TEXT,
    auto_detected   BOOLEAN DEFAULT TRUE,
    false_positive  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_violation_plot ON violation (plot_id);
CREATE INDEX IF NOT EXISTS idx_violation_status ON violation (status);
CREATE INDEX IF NOT EXISTS idx_violation_severity ON violation (severity);
CREATE INDEX IF NOT EXISTS idx_violation_geom ON violation USING GIST (encroachment_geom);
CREATE INDEX IF NOT EXISTS idx_violation_date ON violation (snapshot_date DESC);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: compliance_status
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS compliance_status (
    compliance_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id         UUID NOT NULL UNIQUE REFERENCES plot(plot_id),
    overall_score   DOUBLE PRECISION,
    boundary_score  DOUBLE PRECISION,
    utilization_score DOUBLE PRECISION,
    payment_score   DOUBLE PRECISION,
    category        VARCHAR(20),
    active_violations INTEGER DEFAULT 0,
    total_violations INTEGER DEFAULT 0,
    last_assessed_at TIMESTAMPTZ,
    next_review_at  TIMESTAMPTZ,
    assessed_by     VARCHAR(200) DEFAULT 'SYSTEM_AUTO',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compliance_plot ON compliance_status (plot_id);
CREATE INDEX IF NOT EXISTS idx_compliance_score ON compliance_status (overall_score);
CREATE INDEX IF NOT EXISTS idx_compliance_category ON compliance_status (category);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: payment_status
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS payment_status (
    payment_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id         UUID NOT NULL REFERENCES plot(plot_id),
    payment_type    VARCHAR(50),
    amount_inr      NUMERIC(15,2) NOT NULL,
    due_date        DATE NOT NULL,
    paid_date       DATE,
    status          VARCHAR(20) DEFAULT 'PENDING',
    receipt_number  VARCHAR(100),
    fiscal_year     VARCHAR(10) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_plot ON payment_status (plot_id);
CREATE INDEX IF NOT EXISTS idx_payment_status ON payment_status (status);
CREATE INDEX IF NOT EXISTS idx_payment_due_date ON payment_status (due_date);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: audit_log
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_log (
    log_id          SERIAL PRIMARY KEY,
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       UUID NOT NULL,
    action          VARCHAR(50) NOT NULL,
    actor           VARCHAR(200) NOT NULL,
    actor_role      VARCHAR(50),
    details         JSONB DEFAULT '{}',
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log (actor);

-- ═══════════════════════════════════════════════════════════════════
-- TRIGGERS: Updated timestamps
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_industrial_region_updated_at BEFORE UPDATE ON industrial_region
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_plot_updated_at BEFORE UPDATE ON plot
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_violation_updated_at BEFORE UPDATE ON violation
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_status_updated_at BEFORE UPDATE ON compliance_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
