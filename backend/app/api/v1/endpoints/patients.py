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
