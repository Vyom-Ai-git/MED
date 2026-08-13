from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, or_, desc
from typing import Optional, Tuple, List

from app.models.report import Report
from app.models.order import Order
from app.models.patient import Patient

class ReportRepository:
    def get_by_id(self, db: Session, org_id: int, id: int) -> Optional[Report]:
        return (
            db.query(Report)
            .filter(Report.organization_id == org_id, Report.id == id)
            .options(
                joinedload(Report.order).joinedload(Order.items),
                joinedload(Report.patient),
                joinedload(Report.generator),
            )
            .first()
        )

    def get_by_order(self, db: Session, org_id: int, order_id: int) -> Optional[Report]:
        return (
            db.query(Report)
            .filter(Report.organization_id == org_id, Report.order_id == order_id)
            .order_by(desc(Report.version))
            .first()
        )

    def search_reports(
        self,
        db: Session,
        org_id: int,
        q: Optional[str] = None,
        patient_id: Optional[int] = None,
        order_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Report], int]:
        query = db.query(Report).filter(Report.organization_id == org_id)

        if patient_id:
            query = query.filter(Report.patient_id == patient_id)
        if order_id:
            query = query.filter(Report.order_id == order_id)
        if status:
            query = query.filter(Report.status == status)

        if q:
            term = f"%{q}%"
            query = query.join(Report.order).join(Report.patient).filter(
                or_(
                    Report.report_number.ilike(term),
                    Order.order_number.ilike(term),
                    Patient.first_name.ilike(term),
                    Patient.last_name.ilike(term),
                    Patient.patient_id.ilike(term),
                )
            )

        total = query.count()

        items = (
            query.options(
                joinedload(Report.order).joinedload(Order.items),
                joinedload(Report.patient),
                joinedload(Report.generator),
            )
            .order_by(desc(Report.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return items, total


report_repo = ReportRepository()
