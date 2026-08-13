from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user import user_service
from app.repositories.user import user_repo
from app.api.deps import require_roles
from app.models.user import User
from app.models.enums import UserRole, UserStatus
from app.core import events

router = APIRouter()
logger = logging.getLogger("app.api.users")

@router.get("", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    List all users belonging to the current user's organization (ADMIN only).
    """
    return user_repo.get_multi_by_org(db, organization_id=current_user.organization_id)

@router.get("/{id}", response_model=UserResponse)
def get_user(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Get details of a user by ID, enforcing organization tenant bounds (ADMIN only).
    """
    user = user_repo.get_by_org(db, organization_id=current_user.organization_id, id=id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organization"
        )
    return user

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Create a new user within the admin's organization (ADMIN only).
    """
    # Enforce multi-tenancy boundary
    if user_in.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create a user for another organization"
        )
    
    # Check duplicate email
    existing_user = user_repo.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
        
    user = user_service.create_user(db, user_in=user_in)
    
    # Dispatch audit event
    events.dispatch("user.created", {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "organization_id": user.organization_id,
        "actor_id": current_user.id
    })
    
    return user

@router.patch("/{id}", response_model=UserResponse)
def update_user(
    id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Update user details, enforcing organization tenant bounds (ADMIN only).
    """
    user = user_repo.get_by_org(db, organization_id=current_user.organization_id, id=id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organization"
        )
        
    updated_user = user_service.update_user(db, db_obj=user, obj_in=user_in)
    
    # Dispatch audit event
    events.dispatch("user.updated", {
        "user_id": updated_user.id,
        "email": updated_user.email,
        "role": updated_user.role,
        "status": updated_user.status,
        "organization_id": updated_user.organization_id,
        "actor_id": current_user.id
    })
    
    return updated_user

@router.delete("/{id}", response_model=UserResponse)
def deactivate_user(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Deactivate a user (sets status to inactive, ADMIN only).
    """
    user = user_repo.get_by_org(db, organization_id=current_user.organization_id, id=id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organization"
        )
        
    # Prevent self-deactivation
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own administrator account"
        )
        
    # Standard deactivation instead of physical delete
    user.status = UserStatus.INACTIVE.value
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Dispatch audit event
    events.dispatch("user.deactivated", {
        "user_id": user.id,
        "email": user.email,
        "organization_id": user.organization_id,
        "actor_id": current_user.id
    })
    
    return user
