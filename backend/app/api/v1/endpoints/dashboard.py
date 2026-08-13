from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.enums import UserRole
from app.services.dashboard import dashboard_service
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DashboardWorkloadResponse,
    DashboardTATResponse,
    DashboardActivityResponse,
    DashboardCriticalResultsResponse,
    DashboardVerificationQueueResponse,
    DashboardRecentReportsResponse,
)

router = APIRouter()


def _resolve_branch_id(current_user: User, requested_branch_id: Optional[int]) -> Optional[int]:
    """
    Enforces branch access rules:
    Non-admin users are restricted to their own assigned branch_id.
    Admins can filter by requested_branch_id if provided.
    """
    if current_user.role != UserRole.ADMIN.value:
        return current_user.branch_id
    return requested_branch_id


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    branch_id: Optional[int] = Query(None, description="Optional branch filter for Admins"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get high-level summary KPIs for the laboratory. Tenant isolated.
    """
    effective_branch_id = _resolve_branch_id(current_user, branch_id)
    return dashboard_service.get_summary_metrics(
        db, org_id=current_user.organization_id, branch_id=effective_branch_id
    )


@router.get("/workload", response_model=DashboardWorkloadResponse)
def get_dashboard_workload(
    range_type: str = Query("7days", description="today, 7days, 30days, or custom"),
    start_date: Optional[str] = Query(None, description="ISO start date for custom range"),
    end_date: Optional[str] = Query(None, description="ISO end date for custom range"),
    branch_id: Optional[int] = Query(None, description="Optional branch filter for Admins"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get aggregated workload analytics and time-series for orders and samples. Tenant isolated.
    """
    effective_branch_id = _resolve_branch_id(current_user, branch_id)
    return dashboard_service.get_workload_analytics(
        db,
        org_id=current_user.organization_id,
        range_type=range_type,
        start_date_str=start_date,
        end_date_str=end_date,
        branch_id=effective_branch_id,
    )


@router.get("/tat", response_model=DashboardTATResponse)
def get_dashboard_tat(
    range_type: str = Query("30days", description="today, 7days, 30days, or custom"),
    start_date: Optional[str] = Query(None, description="ISO start date for custom range"),
    end_date: Optional[str] = Query(None, description="ISO end date for custom range"),
    branch_id: Optional[int] = Query(None, description="Optional branch filter for Admins"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get Turnaround Time (TAT) metrics across workflow stages. Tenant isolated.
    Returns average_minutes: null if insufficient data.
    """
    effective_branch_id = _resolve_branch_id(current_user, branch_id)
    return dashboard_service.get_tat_metrics(
        db,
        org_id=current_user.organization_id,
        range_type=range_type,
        start_date_str=start_date,
        end_date_str=end_date,
        branch_id=effective_branch_id,
    )


@router.get("/critical", response_model=DashboardCriticalResultsResponse)
def get_dashboard_critical_results(
    limit: int = Query(10, ge=1, le=50),
    branch_id: Optional[int] = Query(None, description="Optional branch filter for Admins"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get active critical results requiring immediate reviewer/technician attention. Tenant isolated.
    """
    effective_branch_id = _resolve_branch_id(current_user, branch_id)
    return dashboard_service.get_critical_results(
        db, org_id=current_user.organization_id, branch_id=effective_branch_id, limit=limit
    )


@router.get("/verification-queue", response_model=DashboardVerificationQueueResponse)
def get_dashboard_verification_queue(
    limit: int = Query(5, ge=1, le=50),
    branch_id: Optional[int] = Query(None, description="Optional branch filter for Admins"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get quick verification queue widget for Reviewer/Admin dashboard. Tenant isolated.
    """
    effective_branch_id = _resolve_branch_id(current_user, branch_id)
    return dashboard_service.get_verification_queue_widget(
        db, org_id=current_user.organization_id, branch_id=effective_branch_id, limit=limit
    )


@router.get("/activity", response_model=DashboardActivityResponse)
def get_dashboard_activity(
    limit: int = Query(10, ge=1, le=50),
    branch_id: Optional[int] = Query(None, description="Optional branch filter for Admins"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get recent safe audit activity feed for the dashboard. Tenant isolated.
    """
    effective_branch_id = _resolve_branch_id(current_user, branch_id)
    return dashboard_service.get_recent_activity(
        db, org_id=current_user.organization_id, branch_id=effective_branch_id, limit=limit
    )


@router.get("/recent-reports", response_model=DashboardRecentReportsResponse)
def get_dashboard_recent_reports(
    limit: int = Query(5, ge=1, le=50),
    branch_id: Optional[int] = Query(None, description="Optional branch filter for Admins"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get recent generated reports for quick view/download. Tenant isolated.
    """
    effective_branch_id = _resolve_branch_id(current_user, branch_id)
    return dashboard_service.get_recent_reports(
        db, org_id=current_user.organization_id, branch_id=effective_branch_id, limit=limit
    )
