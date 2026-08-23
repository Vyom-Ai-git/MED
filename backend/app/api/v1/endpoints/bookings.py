from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import secrets
import logging

from app.core.database import get_db
from app.models.booking import DoctorAppointment, LabBooking
from app.models.doctor import Doctor, DoctorScheduleSlot
from app.models.patient import Patient
from app.models.branch import Branch
from app.schemas.booking import (
    DoctorAppointmentCreate,
    DoctorAppointmentResponse,
    LabBookingCreate,
    LabBookingResponse,
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()
logger = logging.getLogger("app.api.bookings")


@router.post("/doctor", response_model=dict, status_code=status.HTTP_201_CREATED)
def book_doctor_appointment(
    booking_in: DoctorAppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Book a doctor appointment for a patient (Capability 9).
    """
    org_id = current_user.organization_id

    patient = db.query(Patient).filter(Patient.id == booking_in.patient_id, Patient.organization_id == org_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    doctor = db.query(Doctor).filter(Doctor.id == booking_in.doctor_id, Doctor.organization_id == org_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    if booking_in.slot_id:
        slot = db.query(DoctorScheduleSlot).filter(DoctorScheduleSlot.id == booking_in.slot_id).first()
        if not slot or slot.is_booked:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected slot is unavailable or already booked")
        slot.is_booked = True
        db.add(slot)

    booking_num = f"APT-2026-{secrets.randbelow(89999) + 10000}"
    appointment = DoctorAppointment(
        organization_id=org_id,
        booking_number=booking_num,
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=booking_in.slot_id,
        branch_id=booking_in.branch_id or doctor.branch_id,
        appointment_date=booking_in.appointment_date,
        start_time=booking_in.start_time,
        end_time=booking_in.end_time,
        consultation_type=booking_in.consultation_type,
        status="Scheduled",
        payment_status="Pending",
        fee=doctor.consultation_fee,
        notes=booking_in.notes,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    b_name = None
    if appointment.branch_id:
        b = db.query(Branch).filter(Branch.id == appointment.branch_id).first()
        if b:
            b_name = b.name

    return {
        "id": appointment.id,
        "organization_id": appointment.organization_id,
        "booking_number": appointment.booking_number,
        "patient_id": appointment.patient_id,
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "doctor_id": appointment.doctor_id,
        "doctor_name": doctor.name,
        "doctor_specialty": doctor.specialty,
        "branch_id": appointment.branch_id,
        "branch_name": b_name,
        "appointment_date": appointment.appointment_date,
        "start_time": appointment.start_time,
        "end_time": appointment.end_time,
        "consultation_type": appointment.consultation_type,
        "status": appointment.status,
        "fee": float(appointment.fee),
        "notes": appointment.notes,
        "created_at": appointment.created_at,
    }


@router.post("/lab", response_model=dict, status_code=status.HTTP_201_CREATED)
def book_lab_appointment(
    booking_in: LabBookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Book a lab appointment or home sample collection request (Capability 10).
    """
    org_id = current_user.organization_id

    patient = db.query(Patient).filter(Patient.id == booking_in.patient_id, Patient.organization_id == org_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    booking_num = f"LBK-2026-{secrets.randbelow(89999) + 10000}"
    lab_booking = LabBooking(
        organization_id=org_id,
        booking_number=booking_num,
        patient_id=patient.id,
        branch_id=booking_in.branch_id,
        booking_type=booking_in.booking_type,
        preferred_date=booking_in.preferred_date,
        preferred_slot=booking_in.preferred_slot,
        address=booking_in.address or patient.address,
        tests_requested=booking_in.tests_requested,
        status="Pending",
        notes=booking_in.notes,
    )
    db.add(lab_booking)
    db.commit()
    db.refresh(lab_booking)

    b_name = None
    if lab_booking.branch_id:
        b = db.query(Branch).filter(Branch.id == lab_booking.branch_id).first()
        if b:
            b_name = b.name

    return {
        "id": lab_booking.id,
        "organization_id": lab_booking.organization_id,
        "booking_number": lab_booking.booking_number,
        "patient_id": lab_booking.patient_id,
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "patient_phone": patient.phone,
        "branch_id": lab_booking.branch_id,
        "branch_name": b_name,
        "booking_type": lab_booking.booking_type,
        "preferred_date": lab_booking.preferred_date,
        "preferred_slot": lab_booking.preferred_slot,
        "address": lab_booking.address,
        "tests_requested": lab_booking.tests_requested,
        "status": lab_booking.status,
        "notes": lab_booking.notes,
        "created_at": lab_booking.created_at,
    }
