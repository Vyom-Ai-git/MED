from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.base import CRUDBase
from app.models.patient import Patient

class CRUDPatient(CRUDBase[Patient]):
    def get_by_patient_id(self, db: Session, org_id: int, patient_id: str) -> Optional[Patient]:
        return db.query(self.model).filter(
            self.model.organization_id == org_id,
            self.model.patient_id == patient_id
        ).first()

    def search_patients(
        self, db: Session, org_id: int, q: Optional[str] = None, page: int = 1, page_size: int = 10
    ):
        query = db.query(self.model).filter(self.model.organization_id == org_id)
        if q:
            search_filter = f"%{q}%"
            query = query.filter(
                (self.model.patient_id.ilike(search_filter)) |
                (self.model.first_name.ilike(search_filter)) |
                (self.model.last_name.ilike(search_filter)) |
                (self.model.phone.ilike(search_filter)) |
                (self.model.email.ilike(search_filter))
            )
        
        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(self.model.created_at.desc()).offset(offset).limit(page_size).all()
        return items, total

patient_repo = CRUDPatient(Patient)
