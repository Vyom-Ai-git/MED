from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.base import CRUDBase
from app.models.organization import Organization

class CRUDOrganization(CRUDBase[Organization]):
    def get_by_code(self, db: Session, code: str) -> Optional[Organization]:
        return db.query(self.model).filter(self.model.code == code).first()

organization_repo = CRUDOrganization(Organization)
