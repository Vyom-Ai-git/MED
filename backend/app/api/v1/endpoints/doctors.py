from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import logging

from app.core.database import get_db
from app.models.doctor import Doctor, DoctorScheduleSlot
from app.models.branch import Branch
from app.schemas.doctor import DoctorResponse, DoctorScheduleSlotResponse, DoctorCreate
from app.api.deps import get_current_user, get_current_user_or_m2m, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter()
logger = logging.getLogger("app.api.doctors")


@router.get("", response_model=dict)
def get_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_m2m),
    specialty: Optional[str] = None,
    branch_id: Optional[int] = None,
    q: Optional[str] = None,
):
    """
    List doctors available in the organization with filter options.
    """
    query = db.query(Doctor).filter(
        Doctor.organization_id == current_user.organization_id,
        Doctor.is_active == True
    )

    if specialty:
        query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
    if branch_id:
        query = query.filter(Doctor.branch_id == branch_id)
    if q:
        query = query.filter((Doctor.name.ilike(f"%{q}%")) | (Doctor.specialty.ilike(f"%{q}%")))

    doctors = query.all()
    results = []

    for doc in doctors:
        b_name = None
        if doc.branch_id:
            b = db.query(Branch).filter(Branch.id == doc.branch_id).first()
            if b:
                b_name = b.name

        slots_count = db.query(DoctorScheduleSlot).filter(
            DoctorScheduleSlot.doctor_id == doc.id,
            DoctorScheduleSlot.is_booked == False
        ).count()

        results.append({
            "id": doc.id,
            "organization_id": doc.organization_id,
            "branch_id": doc.branch_id,
            "doctor_code": doc.doctor_code,
            "name": doc.name,
            "specialty": doc.specialty,
            "qualification": doc.qualification,
            "phone": doc.phone,
            "email": doc.email,
            "consultation_fee": float(doc.consultation_fee),
            "bio": doc.bio,
            "is_active": doc.is_active,
            "branch_name": b_name,
            "available_slots_count": slots_count,
            "created_at": doc.created_at,
        })

    return {"items": results, "total": len(results)}


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_doctor(
    doc_in: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """
    Register a doctor in the catalog (Admin only).
    """
    import secrets

    doc_code = doc_in.doctor_code or f"DOC-{secrets.randbelow(899999) + 100000}"
    doctor = Doctor(
        organization_id=current_user.organization_id,
        branch_id=doc_in.branch_id,
        doctor_code=doc_code,
        name=doc_in.name,
        specialty=doc_in.specialty,
        qualification=doc_in.qualification,
        phone=doc_in.phone,
        email=doc_in.email,
        consultation_fee=doc_in.consultation_fee,
        bio=doc_in.bio,
        is_active=doc_in.is_active,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    return {
        "id": doctor.id,
        "doctor_code": doctor.doctor_code,
        "name": doctor.name,
        "specialty": doctor.specialty,
        "qualification": doctor.qualification,
        "consultation_fee": float(doctor.consultation_fee),
    }


@router.get("/{id}/availability", response_model=dict)
def get_doctor_availability(
    id: int,
    slot_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_m2m),
):
    """
    Get available time slots for a specific doctor.
    """
    doctor = db.query(Doctor).filter(
        Doctor.id == id,
        Doctor.organization_id == current_user.organization_id
    ).first()

    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    query = db.query(DoctorScheduleSlot).filter(
        DoctorScheduleSlot.doctor_id == doctor.id,
        DoctorScheduleSlot.is_booked == False
    )

    if slot_date:
        query = query.filter(DoctorScheduleSlot.slot_date == slot_date)

    slots = query.all()
    slots_data = []
    for s in slots:
        slots_data.append({
            "id": s.id,
            "doctor_id": s.doctor_id,
            "branch_id": s.branch_id,
            "slot_date": s.slot_date,
            "start_time": str(s.start_time),
            "end_time": str(s.end_time),
            "consultation_type": s.consultation_type,
            "is_booked": s.is_booked,
        })

    return {
        "doctor_id": doctor.id,
        "doctor_name": doctor.name,
        "specialty": doctor.specialty,
        "consultation_fee": float(doctor.consultation_fee),
        "available_slots": slots_data,
    }
