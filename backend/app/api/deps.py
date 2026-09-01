from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.repositories.user import user_repo
from app.models.user import User

from app.models.enums import UserRole

reusable_oauth2 = HTTPBearer()

def get_current_user(
    db: Session = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(reusable_oauth2)
) -> User:
    payload = decode_access_token(token.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = user_repo.get(db, id=int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return user

from typing import Optional
from fastapi import Header
from app.core.config import settings

reusable_oauth2_optional = HTTPBearer(auto_error=False)

def get_current_user_or_m2m(
    db: Session = Depends(get_db),
    token: Optional[HTTPAuthorizationCredentials] = Depends(reusable_oauth2_optional),
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> User:
    configured_key = settings.LABOS_API_KEY
    passed_key = x_integration_key or x_api_key
    if not passed_key and token and token.credentials == configured_key:
        passed_key = token.credentials

    if configured_key and passed_key and passed_key == configured_key:
        system_user = db.query(User).filter(User.role == "admin").first()
        if not system_user:
            system_user = db.query(User).first()
        if system_user:
            if not getattr(system_user, "organization_id", None):
                setattr(system_user, "organization_id", 1)
            return system_user

        class M2MUser:
            id = 1
            organization_id = 1
            role = "admin"
            name = "M2M System"
            email = "m2m@system.local"
            status = "active"
        return M2MUser()

    if token and token.credentials:
        return get_current_user(db=db, token=token)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication credentials",
    )


def require_roles(*roles: UserRole):
    """
    Dependency factory to check if the current user has one of the allowed roles.
    """
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in [r.value for r in roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user
    return dependency
