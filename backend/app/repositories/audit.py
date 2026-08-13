from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from datetime import datetime
from app.models.audit import AuditLog
from app.models.user import User


class AuditRepository:
    def create_audit(
        self,
        db: Session,
        *,
        org_id: int,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        branch_id: Optional[int] = None,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        failure_reason: Optional[str] = None,
    ) -> AuditLog:
        audit = AuditLog(
            organization_id=org_id,
            branch_id=branch_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            event_type=event_type,
            description=description,
            old_values=old_values,
            new_values=new_values,
            metadata_json=metadata_json,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    def get_by_id(self, db: Session, *, org_id: int, audit_id: int) -> Optional[AuditLog]:
        return db.query(AuditLog).filter(
            and_(AuditLog.id == audit_id, AuditLog.organization_id == org_id)
        ).first()

    def search_audit_logs(
        self,
        db: Session,
        *,
        org_id: int,
        q: Optional[str] = None,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        user_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[AuditLog], int]:
        # Enforce maximum page size of 100
        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)

        query = db.query(AuditLog).filter(AuditLog.organization_id == org_id)

        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type.upper())

        if action:
            query = query.filter(AuditLog.action == action.upper())

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if date_from:
            query = query.filter(AuditLog.created_at >= date_from)

        if date_to:
            query = query.filter(AuditLog.created_at <= date_to)

        if q:
            search_term = f"%{q}%"
            query = query.outerjoin(User, AuditLog.user_id == User.id).filter(
                or_(
                    AuditLog.entity_id.ilike(search_term),
                    AuditLog.action.ilike(search_term),
                    AuditLog.description.ilike(search_term),
                    User.name.ilike(search_term),
                    User.email.ilike(search_term),
                )
            )

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size).all()

        return items, total


audit_repo = AuditRepository()
