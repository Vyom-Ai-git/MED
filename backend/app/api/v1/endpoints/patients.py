from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_db
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate, PatientListResponse
from app.repositories.patient import patient_repo
from app.services.patient import patient_service, DuplicatePatientError
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.core import events

router = APIRouter()
logger = logging.getLogger("app.api.patients")

@router.get("", response_model=PatientListResponse)
def get_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
):
    """
    Search and list patients under the user's organization (paginated).
    All authenticated staff can view the patients list.
    """
    items, total = patient_repo.search_patients(
        db, org_id=current_user.organization_id, q=q, page=page, page_size=page_size
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/lookup", response_model=dict)
def lookup_patient_communication(
    phone: Optional[str] = None,
    email: Optional[str] = None,
    patient_id: Optional[str] = None,
    order_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Patient communication and contact lookup by phone, email, MRN (patient_id), or order_id.
    """
    from app.models.patient import Patient
    from app.models.order import Order

    query = db.query(Patient).filter(Patient.organization_id == current_user.organization_id)

    if order_id:
        order = db.query(Order).filter(Order.id == order_id, Order.organization_id == current_user.organization_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        query = query.filter(Patient.id == order.patient_id)
    elif patient_id:
        query = query.filter(Patient.patient_id == patient_id)
    elif phone:
        raw_phone = phone.strip()
        clean_phone = raw_phone.replace("+", "").replace(" ", "")
        query = query.filter(
            (Patient.phone.contains(raw_phone)) |
            (Patient.phone.contains(clean_phone)) |
            (Patient.phone.contains(raw_phone.replace(" ", "+")))
        )
    elif email:
        query = query.filter(Patient.email.ilike(f"%{email}%"))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide at least one search query: phone, email, patient_id, or order_id"
        )

    patient = query.first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient record not found")

    recent_orders_count = db.query(Order).filter(Order.patient_id == patient.id).count()

    return {
        "id": patient.id,
        "patient_id": patient.patient_id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "full_name": f"{patient.first_name} {patient.last_name}",
        "date_of_birth": patient.date_of_birth,
        "gender": patient.gender,
        "phone": patient.phone,
        "email": patient.email,
        "address": patient.address,
        "emergency_contact": patient.emergency_contact,
        "communication_preference": patient.communication_preference,
        "consent_operational": patient.consent_operational,
        "consent_promotional": patient.consent_promotional,
        "recent_orders_count": recent_orders_count,
    }


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTION))
):
    """
    Register a new patient under the current organization (ADMIN or RECEPTION only).
    """
    # Enforce multi-tenancy boundary
    if patient_in.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot register patient for another organization"
        )
        
    try:
        patient = patient_service.create_patient(
            db, 
            patient_in=patient_in, 
            org_id=current_user.organization_id,
            ignore_duplicate=patient_in.ignore_duplicate
        )
        
        # Dispatch audit event
        events.dispatch("patient.created", {
            "patient_id": patient.id,
            "patient_uid": patient.patient_id,
            "organization_id": patient.organization_id,
            "actor_id": current_user.id
        })
        
        return patient
    except DuplicatePatientError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "existing_id": e.existing_id
            }
        )

@router.get("/{id}", response_model=PatientResponse)
def get_patient(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed profile of a specific patient.
    """
    patient = patient_repo.get_by_org(db, organization_id=current_user.organization_id, id=id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or belongs to another organization"
        )
        
    # Dispatch audit event
    events.dispatch("patient.viewed", {
        "patient_id": patient.id,
        "organization_id": patient.organization_id,
        "actor_id": current_user.id
    })
    
    return patient

@router.patch("/{id}", response_model=PatientResponse)
def update_patient(
    id: int,
    patient_in: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTION))
):
    """
    Update patient details, enforcing organization bounds (ADMIN or RECEPTION only).
    """
    patient = patient_repo.get_by_org(db, organization_id=current_user.organization_id, id=id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or belongs to another organization"
        )
        
    updated_patient = patient_repo.update(db, db_obj=patient, obj_in=patient_in)
    
    # Dispatch audit event
    events.dispatch("patient.updated", {
        "patient_id": updated_patient.id,
        "organization_id": updated_patient.organization_id,
        "actor_id": current_user.id
    })
    
    return updated_patient
