from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Sample(Base):
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    sample_identifier = Column(String, unique=True, index=True, nullable=False)  # e.g. SMP-20260813-00001
    sample_type = Column(String, nullable=False)  # e.g. Blood, Serum, Plasma, Urine, Stool, Swab, Other
    collection_status = Column(String, default="Registered", nullable=False)
    # Controlled states: Registered → Collected → Processing → Completed, or Rejected, Recollection Required, Cancelled
    priority = Column(String, default="Normal", nullable=False)  # Normal, Urgent

    collected_at = Column(DateTime, nullable=True)
    collected_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)

    rejection_reason = Column(Text, nullable=True)
    recollection_required = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    branch = relationship("Branch")
    order = relationship("Order", back_populates="samples")
    collector = relationship("User", foreign_keys=[collected_by])
    results = relationship("Result", back_populates="sample", cascade="all, delete-orphan")


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    sample_id = Column(Integer, ForeignKey("samples.id", ondelete="CASCADE"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    parameter_id = Column(Integer, ForeignKey("test_parameters.id", ondelete="CASCADE"), nullable=False)

    raw_value = Column(String, nullable=True)
    numeric_value = Column(Numeric(10, 2), nullable=True)
    text_value = Column(Text, nullable=True)

    # Snapshot fields for historical accuracy
    unit = Column(String, nullable=True)
    reference_low = Column(Numeric(10, 2), nullable=True)
    reference_high = Column(Numeric(10, 2), nullable=True)

    abnormal_flag = Column(String, default="NORMAL", nullable=False)  # NORMAL, LOW, HIGH
    critical_flag = Column(Boolean, default=False, nullable=False)
    status = Column(String, default="Draft", nullable=False)  # Draft, Entered, Verified, Amended

    entered_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    entered_at = Column(DateTime, nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    correction_reason = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    organization = relationship("Organization")
    sample = relationship("Sample", back_populates="results")
    order_item = relationship("OrderItem")
    test = relationship("Test")
    parameter = relationship("TestParameter")
    author = relationship("User", foreign_keys=[entered_by])
    verifier = relationship("User", foreign_keys=[verified_by])
    verifications = relationship("ResultVerification", back_populates="result", cascade="all, delete-orphan")

