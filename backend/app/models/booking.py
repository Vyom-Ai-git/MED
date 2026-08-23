from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean, Numeric, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class DoctorAppointment(Base):
    __tablename__ = "doctor_appointments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    booking_number = Column(String, unique=True, index=True, nullable=False)  # e.g. APT-2026-00001
    
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(Integer, ForeignKey("doctor_schedule_slots.id", ondelete="SET NULL"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)

    appointment_date = Column(Date, nullable=False)
    start_time = Column(String, nullable=False)  # e.g. "10:00:00"
    end_time = Column(String, nullable=False)    # e.g. "10:30:00"
    consultation_type = Column(String, default="in_person", nullable=False)  # in_person, tele_consult
    
    status = Column(String, default="Scheduled", nullable=False)  # Scheduled, Completed, Cancelled
    payment_status = Column(String, default="Pending", nullable=False)  # Pending, Paid
    fee = Column(Numeric(10, 2), default=500.0, nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    patient = relationship("Patient")
    doctor = relationship("Doctor")
    slot = relationship("DoctorScheduleSlot")
    branch = relationship("Branch")


class LabBooking(Base):
    __tablename__ = "lab_bookings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    booking_number = Column(String, unique=True, index=True, nullable=False)  # e.g. LBK-2026-00001
    
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)

    booking_type = Column(String, default="home_collection", nullable=False)  # home_collection, walk_in
    preferred_date = Column(Date, nullable=False)
    preferred_slot = Column(String, nullable=False)  # e.g. "08:00 AM - 10:00 AM"

    address = Column(JSON, nullable=True)  # {"street": "...", "city": "...", "pincode": "..."}
    tests_requested = Column(JSON, nullable=False)  # list of test IDs or test names
    
    status = Column(String, default="Pending", nullable=False)  # Pending, Confirmed, Collected, Completed, Cancelled
    assigned_phlebotomist_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    patient = relationship("Patient")
    branch = relationship("Branch")
    phlebotomist = relationship("User")
