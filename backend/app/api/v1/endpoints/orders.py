from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    OrderListResponse,
    PaymentStatusUpdate,
    PatientOrderSummary,
)
from app.repositories.order import order_repo
from app.services.order import order_service
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter()
logger = logging.getLogger("app.api.orders")


@router.get("", response_model=OrderListResponse)
def get_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    q: Optional[str] = Query(None, description="Search by order number, patient name, phone, patient ID"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    patient_id: Optional[int] = Query(None, description="Filter by patient DB id"),
    date_from: Optional[datetime] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter to date (ISO format)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """
    Paginated, searchable order registry. All authenticated staff can view.
    """
    items, total = order_repo.search_orders(
        db,
        org_id=current_user.organization_id,
        q=q,
        status=status,
        payment_status=payment_status,
        patient_id=patient_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTION)),
):
    """
    Create a new laboratory order. Admin and Reception only.
    Prices, totals, and order number are calculated server-side.
    """
    try:
        order = order_service.create_order(
            db, order_in=order_in,
            org_id=current_user.organization_id,
            user_id=current_user.id,
        )
        return order_repo.get_with_details(db, organization_id=current_user.organization_id, id=order.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/patient/{patient_id}", response_model=list[PatientOrderSummary])
def get_patient_orders(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all orders for a specific patient (used by patient profile page).
    Tenant-isolated: patient must belong to authenticated organization.
    """
    return order_repo.get_by_patient(db, org_id=current_user.organization_id, patient_id=patient_id)


@router.get("/{id}", response_model=OrderResponse)
def get_order(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed order with patient summary, items with snapshots, and financial breakdown.
    """
    order = order_repo.get_with_details(db, organization_id=current_user.organization_id, id=id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or belongs to another organization",
        )
    return order


@router.patch("/{id}/cancel", response_model=OrderResponse)
def cancel_order(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTION)),
):
    """
    Cancel a Pending order. Only Admin and Reception can cancel.
    Only Pending orders may be cancelled.
    """
    order = order_repo.get_with_details(db, organization_id=current_user.organization_id, id=id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or belongs to another organization",
        )
    try:
        return order_service.cancel_order(db, order=order, user_role=current_user.role)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{id}/payment", response_model=OrderResponse)
def update_payment_status(
    id: int,
    payment_in: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTION)),
):
    """
    Update order payment status. Admin and Reception only.
    """
    order = order_repo.get_with_details(db, organization_id=current_user.organization_id, id=id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or belongs to another organization",
        )
    try:
        return order_service.update_payment_status(db, order=order, payment_status=payment_in.payment_status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{id}/status", response_model=OrderResponse)
def transition_order_status(
    id: int,
    status_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transition order through the laboratory workflow state machine.
    Enforces valid transitions and role-gated permissions.
    """
    order = order_repo.get_with_details(db, organization_id=current_user.organization_id, id=id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or belongs to another organization",
        )

    if not status_update.status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status must be provided")

    try:
        return order_service.transition_status(
            db, order=order,
            target_status=status_update.status,
            user_role=current_user.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
