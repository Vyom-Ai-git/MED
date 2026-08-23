from sqlalchemy import Column, Integer, String, DateTime, Date, Time, ForeignKey, Boolean, Numeric, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    
    doctor_code = Column(String, unique=True, index=True, nullable=False)  # e.g. DOC-2026-001
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)  # e.g. General Physician, Pathologist, Cardiologist
    qualification = Column(String, nullable=False)  # e.g. MBBS, MD
    phone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    consultation_fee = Column(Numeric(10, 2), default=500.0, nullable=False)
    bio = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    branch = relationship("Branch")
    slots = relationship("DoctorScheduleSlot", back_populates="doctor", cascade="all, delete-orphan")


class DoctorScheduleSlot(Base):
    __tablename__ = "doctor_schedule_slots"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)

    slot_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    consultation_type = Column(String, default="in_person", nullable=False)  # in_person, tele_consult
    is_booked = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    doctor = relationship("Doctor", back_populates="slots")
    branch = relationship("Branch")
