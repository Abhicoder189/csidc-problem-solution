"""
ILMCS — Database Models (SQLAlchemy + GeoAlchemy2)
"""

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, Date,
    DateTime, Text, ForeignKey, CheckConstraint, UniqueConstraint,
    Numeric, ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from geoalchemy2 import Geometry
from datetime import datetime
import uuid
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ilmcs_admin:ilmcs_secure_2026@localhost:5432/ilmcs"
)

engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class IndustrialRegion(Base):
    __tablename__ = "industrial_region"

    region_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    type = Column(String(10), nullable=False)
    state = Column(String(100), default="Chhattisgarh")
    district = Column(String(100))
    tehsil = Column(String(100))
    boundary_geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    total_plots = Column(Integer, default=0)
    centroid_lat = Column(Float)
    centroid_lon = Column(Float)
    established_date = Column(Date)
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plots = relationship("Plot", back_populates="region", cascade="all, delete-orphan")
    snapshots = relationship("SatelliteSnapshot", back_populates="region")


class Plot(Base):
    __tablename__ = "plot"

    plot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_id = Column(UUID(as_uuid=True), ForeignKey("industrial_region.region_id", ondelete="CASCADE"), nullable=False)
    plot_number = Column(String(50), nullable=False)
    allottee_name = Column(String(300))
    allottee_entity = Column(String(300))
    allotment_date = Column(Date)
    lease_type = Column(String(50))
    lease_years = Column(Integer)
    lease_expiry = Column(Date)
    approved_purpose = Column(String(200))
    approved_activity = Column(String(200))
    plot_status = Column(String(30), default="ALLOTTED")
    contact_phone = Column(String(20))
    contact_email = Column(String(200))
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    region = relationship("IndustrialRegion", back_populates="plots")
    boundary = relationship("AllotmentBoundary", back_populates="plot", uselist=False)
    violations = relationship("Violation", back_populates="plot")
    compliance = relationship("ComplianceStatus", back_populates="plot", uselist=False)
    payments = relationship("PaymentStatus", back_populates="plot")

    __table_args__ = (UniqueConstraint("region_id", "plot_number"),)


class AllotmentBoundary(Base):
    __tablename__ = "allotment_boundary"

    boundary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plot_id = Column(UUID(as_uuid=True), ForeignKey("plot.plot_id", ondelete="CASCADE"), nullable=False)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)
    source_type = Column(String(30), nullable=False)
    source_file = Column(String(500))
    accuracy_m = Column(Float, default=5.0)
    digitized_by = Column(String(200))
    digitized_at = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)
    verified_by = Column(String(200))
    verified_at = Column(DateTime)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    plot = relationship("Plot", back_populates="boundary")


class SatelliteSnapshot(Base):
    __tablename__ = "satellite_snapshot"

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_id = Column(UUID(as_uuid=True), ForeignKey("industrial_region.region_id"), nullable=False)
    source = Column(String(30), nullable=False)
    captured_at = Column(Date, nullable=False, primary_key=True)
    cloud_cover_pct = Column(Float, default=0)
    resolution_m = Column(Float, nullable=False)
    bands = Column(ARRAY(Text))
    footprint_geom = Column(Geometry("POLYGON", srid=4326))
    raster_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500))
    file_size_mb = Column(Float)
    processing_level = Column(String(10), default="L2A")
    is_processed = Column(Boolean, default=False)
    ndvi_computed = Column(Boolean, default=False)
    segmentation_done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    region = relationship("IndustrialRegion", back_populates="snapshots")


class Violation(Base):
    __tablename__ = "violation"

    violation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plot_id = Column(UUID(as_uuid=True), ForeignKey("plot.plot_id"), nullable=False)
    snapshot_id = Column(UUID(as_uuid=True), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    structure_id = Column(UUID(as_uuid=True))
    violation_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    encroachment_geom = Column(Geometry("POLYGON", srid=4326))
    encroachment_area_sqm = Column(Float, default=0)
    iou_score = Column(Float)
    area_deviation_pct = Column(Float)
    risk_score = Column(Float)
    confidence_score = Column(Float)
    evidence_image_path = Column(String(500))
    overlay_image_path = Column(String(500))
    status = Column(String(30), default="DETECTED")
    detected_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)
    notice_sent_at = Column(DateTime)
    resolved_at = Column(DateTime)
    reviewed_by = Column(String(200))
    review_notes = Column(Text)
    auto_detected = Column(Boolean, default=True)
    false_positive = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plot = relationship("Plot", back_populates="violations")


class ComplianceStatus(Base):
    __tablename__ = "compliance_status"

    compliance_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plot_id = Column(UUID(as_uuid=True), ForeignKey("plot.plot_id"), unique=True, nullable=False)
    overall_score = Column(Float)
    boundary_score = Column(Float)
    utilization_score = Column(Float)
    payment_score = Column(Float)
    category = Column(String(20))
    active_violations = Column(Integer, default=0)
    total_violations = Column(Integer, default=0)
    last_assessed_at = Column(DateTime)
    next_review_at = Column(DateTime)
    assessed_by = Column(String(200), default="SYSTEM_AUTO")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plot = relationship("Plot", back_populates="compliance")


class PaymentStatus(Base):
    __tablename__ = "payment_status"

    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plot_id = Column(UUID(as_uuid=True), ForeignKey("plot.plot_id"), nullable=False)
    payment_type = Column(String(50))
    amount_inr = Column(Numeric(15, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date)
    status = Column(String(20), default="PENDING")
    receipt_number = Column(String(100))
    fiscal_year = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plot = relationship("Plot", back_populates="payments")


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(50), nullable=False)
    actor = Column(String(200), nullable=False)
    actor_role = Column(String(50))
    details = Column(JSONB, default={})
    ip_address = Column(INET)
    created_at = Column(DateTime, default=datetime.utcnow)
