from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth import auth_service
from app.services.audit import audit_service
from app.api.deps import get_current_user
from app.models.user import User
from app.models.user import User as UserModel
from app.repositories.user import user_repo
from app.schemas.user import UserResponse

router = APIRouter()


def get_client_ip(request: Request) -> str:
    # Safely extract IP without blindly trusting client spoofing headers unless behind trusted proxy
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post("/login", response_model=LoginResponse)
def login(request_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Authenticate user and return access token. Audits login attempts safely.
    """
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    user = auth_service.authenticate(db, email=request_data.email, password=request_data.password)
    if not user:
        # Check if user exists to record org_id safely
        existing = user_repo.get_by_email(db, email=request_data.email)
        org_id = existing.organization_id if existing else 1
        user_id = existing.id if existing else None
        reason = "Deactivated user" if (existing and existing.status != "active") else "Invalid credentials"

        audit_service.log(
            db,
            org_id=org_id,
            action="LOGIN_FAILURE",
            entity_type="AUTHENTICATION",
            entity_id=request_data.email,
            user_id=user_id,
            description=f"Login failed for {request_data.email}",
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            failure_reason=reason,
            metadata_json={"email": request_data.email},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = auth_service.generate_token(user)

    audit_service.log(
        db,
        org_id=user.organization_id,
        action="LOGIN_SUCCESS",
        entity_type="AUTHENTICATION",
        entity_id=str(user.id),
        user_id=user.id,
        branch_id=user.branch_id,
        description=f"User {user.email} logged in successfully",
        ip_address=client_ip,
        user_agent=user_agent,
        success=True,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Logout user session and record audit log.
    """
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    audit_service.log(
        db,
        org_id=current_user.organization_id,
        action="LOGOUT",
        entity_type="AUTHENTICATION",
        entity_id=str(current_user.id),
        user_id=current_user.id,
        branch_id=current_user.branch_id,
        description=f"User {current_user.email} logged out",
        ip_address=client_ip,
        user_agent=user_agent,
        success=True,
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged in user profile.
    """
    return current_user

