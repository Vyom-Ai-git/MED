from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)

    report_number = Column(String, unique=True, index=True, nullable=False)  # e.g. RPT-2026-00001
    status = Column(String, default="Available", nullable=False)  # Generated, Available, Superseded
    version = Column(Integer, default=1, nullable=False)

    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # storage key/relative path
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String, default="application/pdf", nullable=False)
    checksum = Column(String, nullable=False)  # SHA-256 hash
    page_count = Column(Integer, default=1, nullable=False)
    secure_token = Column(String, unique=True, index=True, nullable=True)
    secure_token_expires_at = Column(DateTime, nullable=True)

    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    generated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    branch = relationship("Branch")
    order = relationship("Order")
    patient = relationship("Patient")
    generator = relationship("User", foreign_keys=[generated_by])
