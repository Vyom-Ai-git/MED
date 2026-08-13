from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, or_, desc
from typing import Optional, Tuple, List
from datetime import datetime

from app.models.sample import Sample, Result
from app.models.order import Order, OrderItem
from app.models.patient import Patient
from app.models.test import Test, TestParameter

class SampleRepository:
    def get_by_id(self, db: Session, org_id: int, id: int) -> Optional[Sample]:
        return (
            db.query(Sample)
            .filter(Sample.organization_id == org_id, Sample.id == id)
            .options(
                joinedload(Sample.order).joinedload(Order.patient),
                joinedload(Sample.order).joinedload(Order.items),
            )
            .first()
        )

    def search_samples(
        self,
        db: Session,
        org_id: int,
        q: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        sample_type: Optional[str] = None,
        order_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Sample], int]:
        query = db.query(Sample).filter(Sample.organization_id == org_id)

        if order_id:
            query = query.filter(Sample.order_id == order_id)
        if status:
            query = query.filter(Sample.collection_status == status)
        if priority:
            query = query.filter(Sample.priority == priority)
        if sample_type:
            query = query.filter(Sample.sample_type == sample_type)

        if q:
            term = f"%{q}%"
            query = query.join(Sample.order).join(Order.patient).filter(
                or_(
                    Sample.sample_identifier.ilike(term),
                    Order.order_number.ilike(term),
                    Patient.first_name.ilike(term),
                    Patient.last_name.ilike(term),
                    Patient.patient_id.ilike(term),
                    Patient.phone.ilike(term),
                )
            )

        total = query.count()

        items = (
            query.options(
                joinedload(Sample.order).joinedload(Order.patient),
                joinedload(Sample.order).joinedload(Order.items),
            )
            .order_by(desc(Sample.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return items, total

    def get_results_by_sample(self, db: Session, org_id: int, sample_id: int) -> List[Result]:
        return (
            db.query(Result)
            .filter(Result.organization_id == org_id, Result.sample_id == sample_id)
            .options(
                joinedload(Result.parameter),
                joinedload(Result.test),
            )
            .all()
        )


sample_repo = SampleRepository()
