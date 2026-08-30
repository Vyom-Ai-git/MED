from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
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


DOCTOR_APPOINTMENT_STATUSES = {"Scheduled", "Completed", "Cancelled", "No-Show"}
LAB_BOOKING_STATUSES = {"Pending", "Confirmed", "Collected", "Completed", "Cancelled"}


@router.get("", response_model=dict)
def list_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    booking_kind: str = Query("all", pattern="^(all|doctor|lab)$"),
    status_filter: Optional[str] = Query(None, alias="status"),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
):
    """
    Unified list of appointments: doctor consultations + home/walk-in lab
    collections, for the Appointments module. Tenant isolated.
    """
    org_id = current_user.organization_id
    items: List[dict] = []

    if booking_kind in ("all", "doctor"):
        q = db.query(DoctorAppointment).filter(DoctorAppointment.organization_id == org_id)
        if status_filter:
            q = q.filter(DoctorAppointment.status == status_filter)
        if from_date:
            q = q.filter(DoctorAppointment.appointment_date >= from_date)
        if to_date:
            q = q.filter(DoctorAppointment.appointment_date <= to_date)
        for appt in q.order_by(DoctorAppointment.appointment_date.desc()).all():
            patient = db.query(Patient).filter(Patient.id == appt.patient_id).first()
            doctor = db.query(Doctor).filter(Doctor.id == appt.doctor_id).first()
            branch = db.query(Branch).filter(Branch.id == appt.branch_id).first() if appt.branch_id else None
            items.append({
                "kind": "doctor",
                "id": appt.id,
                "booking_number": appt.booking_number,
                "patient_id": appt.patient_id,
                "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
                "patient_phone": patient.phone if patient else None,
                "doctor_id": appt.doctor_id,
                "doctor_name": doctor.name if doctor else "Unknown",
                "doctor_specialty": doctor.specialty if doctor else None,
                "branch_name": branch.name if branch else None,
                "date": appt.appointment_date,
                "start_time": appt.start_time,
                "end_time": appt.end_time,
                "consultation_type": appt.consultation_type,
                "status": appt.status,
                "payment_status": appt.payment_status,
                "fee": float(appt.fee),
                "notes": appt.notes,
                "created_at": appt.created_at,
            })

    if booking_kind in ("all", "lab"):
        q = db.query(LabBooking).filter(LabBooking.organization_id == org_id)
        if status_filter:
            q = q.filter(LabBooking.status == status_filter)
        if from_date:
            q = q.filter(LabBooking.preferred_date >= from_date)
        if to_date:
            q = q.filter(LabBooking.preferred_date <= to_date)
        for lb in q.order_by(LabBooking.preferred_date.desc()).all():
            patient = db.query(Patient).filter(Patient.id == lb.patient_id).first()
            branch = db.query(Branch).filter(Branch.id == lb.branch_id).first() if lb.branch_id else None
            items.append({
                "kind": "lab",
                "id": lb.id,
                "booking_number": lb.booking_number,
                "patient_id": lb.patient_id,
                "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
                "patient_phone": patient.phone if patient else None,
                "booking_type": lb.booking_type,
                "branch_name": branch.name if branch else None,
                "date": lb.preferred_date,
                "preferred_slot": lb.preferred_slot,
                "tests_requested": lb.tests_requested,
                "status": lb.status,
                "notes": lb.notes,
                "created_at": lb.created_at,
            })

    items.sort(key=lambda x: str(x["date"]), reverse=True)
    return {"items": items, "total": len(items)}


@router.patch("/doctor/{id}/status", response_model=dict)
def update_doctor_appointment_status(
    id: int,
    new_status: str = Query(..., alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if new_status not in DOCTOR_APPOINTMENT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status. Must be one of {sorted(DOCTOR_APPOINTMENT_STATUSES)}")

    appt = db.query(DoctorAppointment).filter(
        DoctorAppointment.id == id, DoctorAppointment.organization_id == current_user.organization_id
    ).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    appt.status = new_status
    db.commit()
    db.refresh(appt)
    return {"id": appt.id, "status": appt.status}


@router.patch("/lab/{id}/status", response_model=dict)
def update_lab_booking_status(
    id: int,
    new_status: str = Query(..., alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if new_status not in LAB_BOOKING_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status. Must be one of {sorted(LAB_BOOKING_STATUSES)}")

    lb = db.query(LabBooking).filter(
        LabBooking.id == id, LabBooking.organization_id == current_user.organization_id
    ).first()
    if not lb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab booking not found")

    lb.status = new_status
    db.commit()
    db.refresh(lb)
    return {"id": lb.id, "status": lb.status}


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
