from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.base import CRUDBase
from app.models.test import Test

class CRUDTest(CRUDBase[Test]):
    def get_by_code(self, db: Session, org_id: int, code: str) -> Optional[Test]:
        return db.query(self.model).filter(
            self.model.organization_id == org_id,
            self.model.code == code
        ).first()

    def search_tests(
        self, 
        db: Session, 
        org_id: int, 
        q: Optional[str] = None, 
        category: Optional[str] = None, 
        status: Optional[str] = None,
        page: int = 1, 
        page_size: int = 10
    ):
        query = db.query(self.model).filter(self.model.organization_id == org_id)
        if q:
            search_filter = f"%{q}%"
            query = query.filter(
                (self.model.code.ilike(search_filter)) |
                (self.model.name.ilike(search_filter)) |
                (self.model.description.ilike(search_filter))
            )
        if category:
            query = query.filter(self.model.category == category)
        if status:
            query = query.filter(self.model.status == status)
            
        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(self.model.code.asc()).offset(offset).limit(page_size).all()
        return items, total

test_repo = CRUDTest(Test)
