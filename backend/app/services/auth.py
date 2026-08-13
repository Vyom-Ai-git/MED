from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.user import user_repo
from app.core.security import verify_password, create_access_token
from app.models.user import User

class AuthService:
    def authenticate(self, db: Session, email: str, password: str) -> Optional[User]:
        user = user_repo.get_by_email(db, email)
        if not user:
            return None
        if user.status != "active":
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def generate_token(self, user: User) -> str:
        # Include organization_id and branch_id inside token payload for multi-tenant mapping
        payload = {
            "sub": str(user.id),
            "org_id": user.organization_id,
            "branch_id": user.branch_id,
            "role": user.role
        }
        # In our create_access_token helper, we just pass the subject.
        # Let's adjust create_access_token in app.core.security to take a dictionary if needed, 
        # or we can pass the dictionary directly to jwt encode.
        # Since we wrote:
        # def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
        #   to_encode = {"sub": str(subject)}
        # Let's see: we can pass user.id as subject, but it is useful to include tenant info in the JWT!
        # Let's import create_access_token, but let's check: we can use a custom JWT encoder here or 
        # modify create_access_token. Let's look at app.core.security: it takes subject. We can encode 
        # org_id inside the JWT by passing a serialized dictionary or updating create_access_token.
        # Let's see, we can just pass the user ID as subject, and then look up the user in the database 
        # on each request (which is standard and extremely secure as it ensures status checks).
        # Yes! Passing user.id as the subject is clean, standard, and highly secure. Let's do that!
        import datetime
        from app.core.config import settings
        from datetime import timedelta
        
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(subject=user.id, expires_delta=expires_delta)

auth_service = AuthService()
