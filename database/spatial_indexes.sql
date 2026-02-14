-- ============================================================
-- ILMCS Spatial Indexes
-- ============================================================

-- GiST Spatial Indexes
CREATE INDEX idx_region_boundary_geom ON industrial_region USING GIST (boundary_geom);
CREATE INDEX idx_allotment_boundary_geom ON allotment_boundary USING GIST (geom);
CREATE INDEX idx_detected_structure_geom ON detected_structure USING GIST (geom);
CREATE INDEX idx_violation_encroachment_geom ON violation USING GIST (encroachment_geom);
CREATE INDEX idx_snapshot_footprint_geom ON satellite_snapshot USING GIST (footprint_geom);

-- B-Tree Indexes
CREATE INDEX idx_plot_region ON plot(region_id);
CREATE INDEX idx_plot_status ON plot(plot_status);
CREATE INDEX idx_boundary_plot ON allotment_boundary(plot_id);
CREATE INDEX idx_boundary_active ON allotment_boundary(is_active);
CREATE INDEX idx_snapshot_region ON satellite_snapshot(region_id);
CREATE INDEX idx_detected_plot ON detected_structure(plot_id);
CREATE INDEX idx_detected_class ON detected_structure(class_label);
CREATE INDEX idx_violation_plot ON violation(plot_id);
CREATE INDEX idx_violation_type ON violation(violation_type);
CREATE INDEX idx_violation_status ON violation(status);
CREATE INDEX idx_violation_severity ON violation(severity);
CREATE INDEX idx_compliance_category ON compliance_status(category);
CREATE INDEX idx_payment_plot ON payment_status(plot_id);
CREATE INDEX idx_payment_status ON payment_status(status);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);

-- Composite Indexes
CREATE INDEX idx_violation_plot_status ON violation(plot_id, status, detected_at DESC);
CREATE INDEX idx_snapshot_region_date ON satellite_snapshot(region_id, captured_at DESC);

-- ============================================================
-- Custom GIS Functions
-- ============================================================

CREATE OR REPLACE FUNCTION compute_iou(geom_a GEOMETRY, geom_b GEOMETRY)
RETURNS FLOAT AS $$
DECLARE
    intersection_area FLOAT;
    union_area FLOAT;
BEGIN
    IF NOT ST_Intersects(geom_a, geom_b) THEN RETURN 0; END IF;
    intersection_area := ST_Area(ST_Intersection(ST_Transform(geom_a, 32644), ST_Transform(geom_b, 32644)));
    union_area := ST_Area(ST_Transform(geom_a, 32644)) + ST_Area(ST_Transform(geom_b, 32644)) - intersection_area;
    IF union_area = 0 THEN RETURN 0; END IF;
    RETURN intersection_area / union_area;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION compute_area_deviation(allotment GEOMETRY, detected GEOMETRY)
RETURNS FLOAT AS $$
DECLARE
    a_area FLOAT;
    d_area FLOAT;
BEGIN
    a_area := ST_Area(ST_Transform(allotment, 32644));
    d_area := ST_Area(ST_Transform(detected, 32644));
    IF a_area = 0 THEN RETURN 0; END IF;
    RETURN ((d_area - a_area) / a_area) * 100;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION extract_encroachment(
    allotment GEOMETRY, detected GEOMETRY, tolerance_m FLOAT DEFAULT 5.0
) RETURNS GEOMETRY AS $$
DECLARE
    buffered GEOMETRY;
    encroachment GEOMETRY;
BEGIN
    buffered := ST_Transform(ST_Buffer(ST_Transform(allotment, 32644), tolerance_m), 4326);
    IF ST_Contains(buffered, detected) THEN RETURN NULL; END IF;
    encroachment := ST_Difference(ST_Transform(detected, 32644), ST_Transform(buffered, 32644));
    IF ST_IsEmpty(encroachment) THEN RETURN NULL; END IF;
    RETURN ST_Transform(encroachment, 4326);
END;
$$ LANGUAGE plpgsql IMMUTABLE;
