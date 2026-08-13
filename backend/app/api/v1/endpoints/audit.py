from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.repositories.audit import audit_repo
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter()


@router.get("", response_model=AuditLogListResponse)
def get_audit_logs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
    q: Optional[str] = Query(None, description="Search by entity ID, action, description or user"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (PATIENT, ORDER, etc)"),
    action: Optional[str] = Query(None, description="Filter by action (LOGIN_SUCCESS, ORDER_CREATED, etc)"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    date_from: Optional[datetime] = Query(None, description="Filter by start timestamp"),
    date_to: Optional[datetime] = Query(None, description="Filter by end timestamp"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Get paginated, searchable audit log entries. Tenant isolated. Admin & Reviewer access.
    """
    items, total = audit_repo.search_audit_logs(
        db,
        org_id=current_user.organization_id,
        q=q,
        entity_type=entity_type,
        action=action,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )

    response_items = []
    for item in items:
        resp = AuditLogResponse.model_validate(item)
        if item.user:
            resp.user_name = item.user.name
            resp.user_email = item.user.email
        response_items.append(resp)

    return {
        "items": response_items,
        "total": total,
        "page": page,
        "page_size": min(max(page_size, 1), 100),
    }


@router.get("/{id}", response_model=AuditLogResponse)
def get_audit_log_detail(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
):
    """
    Get single audit log entry detail by ID. Enforces tenant isolation (404/403 if invalid).
    """
    audit = audit_repo.get_by_id(db, org_id=current_user.organization_id, audit_id=id)
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log record not found or access denied",
        )

    resp = AuditLogResponse.model_validate(audit)
    if audit.user:
        resp.user_name = audit.user.name
        resp.user_email = audit.user.email
    return resp
