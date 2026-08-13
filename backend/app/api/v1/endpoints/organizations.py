from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.organization import OrganizationResponse, OrganizationUpdate
from app.repositories.organization import organization_repo
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter()

@router.get("/me", response_model=OrganizationResponse)
def get_my_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the organization details of the current logged-in user.
    """
    org = organization_repo.get(db, id=current_user.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.put("/me", response_model=OrganizationResponse)
def update_my_organization(
    org_in: OrganizationUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    Update the organization details of the current user (admin role required).
    """
    org = organization_repo.get(db, id=current_user.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization_repo.update(db, db_obj=org, obj_in=org_in)
