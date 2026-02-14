-- ═══════════════════════════════════════════════════════════════════
-- ILMCS Database Schema v3 — Production PostGIS
-- Industrial Land Monitoring & Compliance System
-- Chhattisgarh — 56 Industrial Regions (36 New + 20 Old)
-- ═══════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: industrial_region (matches SQLAlchemy ORM model)
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
-- TABLE: plot (matches SQLAlchemy ORM model)
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

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: allotment_boundary (matches SQLAlchemy ORM model)
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
    area_sqm        DOUBLE PRECISION,
    perimeter_m     DOUBLE PRECISION,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_allotment_boundary_geom ON allotment_boundary USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_allotment_boundary_plot ON allotment_boundary (plot_id);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: satellite_snapshot (matches SQLAlchemy ORM model)
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
    cloud_cover_pct DECIMAL(5,2),
    bbox            GEOMETRY(Polygon, 4326) NOT NULL,
    image_url       TEXT NOT NULL,
    thumbnail_url   TEXT,
    ndvi_url        TEXT,
    bands           TEXT[] DEFAULT ARRAY['B2','B3','B4','B8'],
    resolution_m    DECIMAL(5,2) DEFAULT 10.0,
    processing_level VARCHAR(10) DEFAULT 'L2A',
    file_size_mb    DECIMAL(8,2),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, acquisition_date)
) PARTITION BY RANGE (acquisition_date);

CREATE TABLE IF NOT EXISTS snapshots_2024 PARTITION OF satellite_snapshots
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE IF NOT EXISTS snapshots_2025 PARTITION OF satellite_snapshots
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE IF NOT EXISTS snapshots_2026 PARTITION OF satellite_snapshots
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE INDEX IF NOT EXISTS idx_snapshots_geom ON satellite_snapshots USING GIST (bbox);
CREATE INDEX IF NOT EXISTS idx_snapshots_region_date ON satellite_snapshots (region_id, acquisition_date DESC);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: detected_footprints (AI-generated building footprints)
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS detected_footprints (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_id     UUID NOT NULL,
    plot_id         UUID REFERENCES plots(id),
    footprint       GEOMETRY(Polygon, 4326) NOT NULL,
    area_sqm        DECIMAL(12,2) NOT NULL,
    confidence      DECIMAL(5,4) NOT NULL,
    model_name      VARCHAR(100) NOT NULL,
    land_class      VARCHAR(30),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_footprints_geom ON detected_footprints USING GIST (footprint);
CREATE INDEX IF NOT EXISTS idx_footprints_snapshot ON detected_footprints (snapshot_id);
-- ═══════════════════════════════════════════════════════════════════
-- TABLE: violation (matches SQLAlchemy ORM model)
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
    severity        VARCHAR(10) NOT NULL CHECK (severity IN ('critical','high','medium','low')),
    affected_area_sqm DECIMAL(12,2),
    encroachment_geom GEOMETRY(Polygon, 4326),
    iou_score       DECIMAL(5,4),
    area_deviation_pct DECIMAL(7,2),
    confidence      DECIMAL(5,4),
    description     TEXT,
    evidence_urls   TEXT[],
    detected_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    status          VARCHAR(20) DEFAULT 'open' CHECK (status IN (
                      'open','acknowledged','under_review','resolved','escalated','legal')),
    assigned_to     VARCHAR(255),
    resolution_notes TEXT,
    resolved_date   DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_violations_geom ON violations USING GIST (encroachment_geom);
CREATE INDEX IF NOT EXISTS idx_violations_plot ON violations (plot_id);
CREATE INDEX IF NOT EXISTS idx_violations_severity ON violations (severity, status);
CREATE INDEX IF NOT EXISTS idx_violations_date ON violations (detected_date DESC);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: compliance_status (matches SQLAlchemy ORM model)
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

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: payment_status (matches SQLAlchemy ORM model)
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

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: audit_log (matches SQLAlchemy ORM model)
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
    activity_status VARCHAR(20) CHECK (activity_status IN (
                      'operational','partially_operational','closed','under_construction','vacant')),
    ndvi_mean       DECIMAL(5,4),
    ndbi_mean       DECIMAL(5,4),
    notes           TEXT,
    assessed_by     VARCHAR(50) DEFAULT 'system',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compliance_plot_date ON compliance_status (plot_id, assessment_date DESC);
CREATE INDEX IF NOT EXISTS idx_compliance_risk ON compliance_status (risk_level);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: payment_status
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS payment_status (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id         UUID NOT NULL REFERENCES plots(id),
    payment_type    VARCHAR(30) NOT NULL CHECK (payment_type IN (
                      'lease_rent','maintenance','penalty','development_charge')),
    amount_inr      DECIMAL(14,2) NOT NULL,
    due_date        DATE NOT NULL,
    paid_date       DATE,
    status          VARCHAR(15) DEFAULT 'pending' CHECK (status IN (
                      'pending','paid','overdue','waived','disputed')),
    receipt_number  VARCHAR(100),
    financial_year  VARCHAR(9),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_plot ON payment_status (plot_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payment_status (status, due_date);

-- ═══════════════════════════════════════════════════════════════════
-- TABLE: audit_logs (partitioned)
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_logs (
    id              BIGSERIAL,
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       UUID NOT NULL,
    action          VARCHAR(20) NOT NULL,
    actor           VARCHAR(255) NOT NULL,
    details         JSONB DEFAULT '{}',
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE IF NOT EXISTS audit_logs_2025 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE IF NOT EXISTS audit_logs_2026 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

-- ═══════════════════════════════════════════════════════════════════
-- SEED DATA: All 56 industrial regions
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO industrial_regions (name, code, category, district, center_point) VALUES
('Khapri Khurd','CG-KHK-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.71,21.16),4326)),
('Narayanbahali','CG-NRB-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.55,21.30),4326)),
('Aurethi Bhatapara','CG-AUR-001','new','Balodabazar',ST_SetSRID(ST_MakePoint(81.95,21.73),4326)),
('Siyarpali-Mahuapali','CG-SYM-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.68,21.42),4326)),
('Rikhi','CG-RKH-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.60,21.35),4326)),
('Metal Park Phase II Sector A','CG-MP2A-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.72,21.33),4326)),
('Metal Park Phase II Sector B','CG-MP2B-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.73,21.34),4326)),
('Food Park Sector 1','CG-FP1-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.65,21.31),4326)),
('Food Park Sector 2','CG-FP2-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.66,21.30),4326)),
('Pangrikhurd','CG-PGK-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.57,21.28),4326)),
('Barbaspur','CG-BBP-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.59,21.38),4326)),
('Gangapur Khurd Ambikapur','CG-GKA-001','new','Surguja',ST_SetSRID(ST_MakePoint(83.18,23.10),4326)),
('Textile Park','CG-TXP-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.63,21.32),4326)),
('Tilda','CG-TLD-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.62,21.46),4326)),
('Industrial Area Abhanpur','CG-ABH-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.74,21.09),4326)),
('Teknar','CG-TKN-001','new','Durg',ST_SetSRID(ST_MakePoint(81.32,21.23),4326)),
('Lakhanpuri','CG-LKP-001','new','Durg',ST_SetSRID(ST_MakePoint(81.48,21.27),4326)),
('Hathkera-Bidbida','CG-HKB-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.70,21.40),4326)),
('Kesda','CG-KSD-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.65,21.20),4326)),
('Engineering Park','CG-ENP-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.68,21.31),4326)),
('Silpahari','CG-SLP-001','new','Raigarh',ST_SetSRID(ST_MakePoint(83.38,21.90),4326)),
('Parasgarhi','CG-PRG-001','new','Mahasamund',ST_SetSRID(ST_MakePoint(82.08,21.15),4326)),
('Mahroomkhurd','CG-MRK-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.54,21.25),4326)),
('Rail Park','CG-RLP-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.61,21.47),4326)),
('Khamaria','CG-KHM-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.58,21.37),4326)),
('Readymade Garments Park Nava Raipur','CG-RGP-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.79,21.18),4326)),
('Pharmaceutical Park Nava Raipur','CG-PHP-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.78,21.17),4326)),
('G-Jamgoan','CG-GJM-001','new','Durg',ST_SetSRID(ST_MakePoint(81.40,21.22),4326)),
('Farsabahar','CG-FSB-001','new','Jashpur',ST_SetSRID(ST_MakePoint(83.82,23.18),4326)),
('Plastic Park','CG-PLP-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.67,21.33),4326)),
('Selar','CG-SLR-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.53,21.29),4326)),
('Shyamtarai','CG-SYT-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.60,21.45),4326)),
('Food Park Sukma','CG-FPS-001','new','Sukma',ST_SetSRID(ST_MakePoint(81.66,18.87),4326)),
('Ulakiya','CG-ULK-001','new','Raipur',ST_SetSRID(ST_MakePoint(81.63,21.43),4326)),
('Chandanu Raveli','CG-CHR-001','new','Rajnandgaon',ST_SetSRID(ST_MakePoint(81.08,21.10),4326)),
('Parasiya','CG-PRS-001','new','Rajnandgaon',ST_SetSRID(ST_MakePoint(80.95,21.05),4326)),
('Amaseoni','CG-AMS-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.70,21.22),4326)),
('Bhanpuri','CG-BHP-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.61,21.27),4326)),
('Birkoni','CG-BRK-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.68,21.20),4326)),
('Borai','CG-BOR-001','old','Durg',ST_SetSRID(ST_MakePoint(81.35,21.21),4326)),
('Electronic EMC','CG-EMC-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.62,21.26),4326)),
('Gogoan','CG-GOG-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.62,21.19),4326)),
('Gondwara','CG-GDW-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.60,21.23),4326)),
('Harinchhapara','CG-HRC-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.64,21.21),4326)),
('Kapan','CG-KPN-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.63,21.24),4326)),
('Nayanpur-Gibarganj','CG-NYG-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.65,21.26),4326)),
('Ranidurgawati Anjani','CG-RDA-001','old','Korea',ST_SetSRID(ST_MakePoint(83.05,23.58),4326)),
('Rawabhata','CG-RWB-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.69,21.23),4326)),
('Siltara Phase 1','CG-SL1-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.69,21.32),4326)),
('Siltara Phase 2','CG-SL2-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.70,21.33),4326)),
('Sirgitti','CG-SGT-001','old','Bilaspur',ST_SetSRID(ST_MakePoint(82.15,22.10),4326)),
('Sondongari','CG-SDG-001','old','Raigarh',ST_SetSRID(ST_MakePoint(83.39,21.91),4326)),
('Tendua Phase 1','CG-TD1-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.59,21.30),4326)),
('Tendua Phase 2','CG-TD2-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.58,21.31),4326)),
('Tifra','CG-TFR-001','old','Bilaspur',ST_SetSRID(ST_MakePoint(82.14,22.08),4326)),
('Urla','CG-URL-001','old','Raipur',ST_SetSRID(ST_MakePoint(81.58,21.25),4326))
ON CONFLICT (name) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════
-- VIEWS
-- ═══════════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW v_region_summary AS
SELECT r.id, r.name, r.code, r.category, r.district,
       ST_Y(r.center_point) AS lat, ST_X(r.center_point) AS lon,
       COUNT(p.id) AS plot_count,
       COUNT(CASE WHEN p.status = 'operational' THEN 1 END) AS operational_plots,
       COUNT(CASE WHEN p.status = 'vacant' THEN 1 END) AS vacant_plots,
       AVG(p.risk_score) AS avg_risk_score
FROM industrial_regions r
LEFT JOIN plots p ON p.region_id = r.id
GROUP BY r.id;

CREATE OR REPLACE VIEW v_active_violations AS
SELECT v.id, v.violation_type, v.severity, v.affected_area_sqm,
       v.iou_score, v.confidence, v.detected_date, v.status,
       p.plot_number, p.allottee_company,
       r.name AS region_name, r.district
FROM violations v
JOIN plots p ON p.id = v.plot_id
JOIN industrial_regions r ON r.id = p.region_id
WHERE v.status NOT IN ('resolved')
ORDER BY CASE v.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
         v.detected_date DESC;
