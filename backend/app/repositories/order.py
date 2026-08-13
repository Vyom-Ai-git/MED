from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, cast, String
from app.repositories.base import CRUDBase
from app.models.order import Order
from app.models.patient import Patient


class CRUDOrder(CRUDBase[Order]):
    def get_by_order_number(self, db: Session, org_id: int, order_number: str) -> Optional[Order]:
        return db.query(self.model).filter(
            self.model.organization_id == org_id,
            self.model.order_number == order_number
        ).first()

    def get_with_details(self, db: Session, organization_id: int, id: int) -> Optional[Order]:
        """Get a single order with patient + items eagerly loaded."""
        return (
            db.query(self.model)
            .options(
                joinedload(Order.patient),
                joinedload(Order.items),
                joinedload(Order.ordering_user),
            )
            .filter(
                self.model.id == id,
                self.model.organization_id == organization_id,
            )
            .first()
        )

    def search_orders(
        self,
        db: Session,
        org_id: int,
        q: Optional[str] = None,
        status: Optional[str] = None,
        payment_status: Optional[str] = None,
        patient_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Order], int]:
        """
        Paginated order search with multi-field filtering.
        Joins Patient for name/phone search.
        """
        query = (
            db.query(self.model)
            .join(Patient, self.model.patient_id == Patient.id)
            .options(
                joinedload(Order.patient),
                joinedload(Order.items),
                joinedload(Order.ordering_user),
            )
            .filter(self.model.organization_id == org_id)
        )

        if q:
            search_filter = f"%{q}%"
            query = query.filter(
                or_(
                    self.model.order_number.ilike(search_filter),
                    Patient.first_name.ilike(search_filter),
                    Patient.last_name.ilike(search_filter),
                    Patient.patient_id.ilike(search_filter),
                    Patient.phone.ilike(search_filter),
                )
            )

        if status:
            query = query.filter(self.model.status == status)

        if payment_status:
            query = query.filter(self.model.payment_status == payment_status)

        if patient_id:
            query = query.filter(self.model.patient_id == patient_id)

        if date_from:
            query = query.filter(self.model.created_at >= date_from)

        if date_to:
            query = query.filter(self.model.created_at <= date_to)

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(self.model.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def get_by_patient(self, db: Session, org_id: int, patient_id: int) -> List[Order]:
        """Get all orders for a specific patient (for patient profile view)."""
        return (
            db.query(self.model)
            .options(joinedload(Order.items))
            .filter(
                self.model.organization_id == org_id,
                self.model.patient_id == patient_id,
            )
            .order_by(self.model.created_at.desc())
            .all()
        )


order_repo = CRUDOrder(Order)
