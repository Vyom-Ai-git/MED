from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.branch import BranchCreate, BranchResponse, BranchUpdate
from app.repositories.branch import branch_repo
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter()

@router.get("", response_model=List[BranchResponse])
def get_branches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all branches of the current organization.
    """
    return branch_repo.get_multi_by_org(db, organization_id=current_user.organization_id)

@router.get("/availability", response_model=List[dict])
def get_branches_availability(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed branch/location availability including operating hours, services, and contact info.
    """
    branches = branch_repo.get_multi_by_org(db, organization_id=current_user.organization_id)
    results = []
    for b in branches:
        contact = b.contact_info or {}
        results.append({
            "id": b.id,
            "organization_id": b.organization_id,
            "code": b.code,
            "name": b.name,
            "address": b.address,
            "phone": contact.get("phone"),
            "email": contact.get("email"),
            "status": b.status,
            "is_active": b.status == "active",
            "operating_hours": "07:00 AM - 08:00 PM",
            "services_offered": ["Diagnostic Testing", "Home Sample Collection", "Doctor Consultation", "ECG / Radiology"],
            "has_home_collection": True,
            "has_doctor_consultation": True,
        })
    return results


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch(
    branch_in: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Create a new branch (admin role required).
    """
    # Enforce multi-tenancy: cannot create branch for another org
    if branch_in.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create branch for another organization"
        )
    return branch_repo.create(db, obj_in=branch_in)
