from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(String, unique=True, index=True, nullable=False) # e.g. PAT-2026-0001
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String, nullable=False) # male, female, other
    phone = Column(String, index=True, nullable=False)
    email = Column(String, index=True, nullable=True)
    address = Column(JSON, nullable=True) # {"street": "...", "city": "..."}
    emergency_contact = Column(JSON, nullable=True) # {"name": "...", "phone": "...", "relation": "..."}
    referring_provider = Column(String, nullable=True)
    communication_preference = Column(String, default="email", nullable=False) # whatsapp, email, sms
    consent_operational = Column(Boolean, default=True, nullable=False)
    consent_promotional = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="patients")
    orders = relationship("Order", back_populates="patient", cascade="all, delete-orphan")
