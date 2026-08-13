from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.base import CRUDBase
from app.models.user import User

class CRUDUser(CRUDBase[User]):
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(self.model).filter(self.model.email == email).first()

user_repo = CRUDUser(User)
