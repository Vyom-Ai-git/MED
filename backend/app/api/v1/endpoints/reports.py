from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from app.core.database import get_db
from app.schemas.report import (
    ReportResponse,
    ReportListResponse,
)
from app.repositories.report import report_repo
from app.services.report import report_service
from app.services.storage import storage_service
from app.services.audit import audit_service
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter()
logger = logging.getLogger("app.api.reports")


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.get("", response_model=ReportListResponse)
def get_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    q: Optional[str] = Query(None, description="Search by report number, order number, patient name/id"),
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    order_id: Optional[int] = Query(None, description="Filter by order ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """
    Get paginated, searchable registry of generated laboratory reports. Tenant isolated.
    """
    items, total = report_repo.search_reports(
        db,
        org_id=current_user.organization_id,
        q=q,
        patient_id=patient_id,
        order_id=order_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    response_items = []
    for r in items:
        resp = ReportResponse.model_validate(r)
        if r.generator:
            resp.generated_by_name = r.generator.name
        if r.order:
            tests_list = [item.test_name_snapshot for item in r.order.items]
            pat_summary = None
            if r.patient:
                pat_summary = {
                    "id": r.patient.id,
                    "patient_id": r.patient.patient_id,
                    "first_name": r.patient.first_name,
                    "last_name": r.patient.last_name,
                    "phone": r.patient.phone,
                    "gender": r.patient.gender,
                }
            resp.order = {
                "id": r.order.id,
                "order_number": r.order.order_number,
                "created_at": r.order.created_at,
                "patient": pat_summary,
                "tests": tests_list,
            }
        response_items.append(resp)

    return {"items": response_items, "total": total, "page": page, "page_size": page_size}


@router.post("/generate/{order_id}", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def generate_report(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
):
    """
    Generate PDF laboratory report for a Verified Order. Admin & Reviewer only.
    Rejects unverified orders with HTTP 409 Conflict.
    """
    try:
        report = report_service.generate_report_for_order(
            db, order_id=order_id, org_id=current_user.organization_id, user_id=current_user.id
        )
        return report_repo.get_by_id(db, org_id=current_user.organization_id, id=report.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/order/{order_id}", response_model=ReportResponse)
def get_report_by_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get latest report for an order if available.
    """
    report = report_repo.get_by_order(db, org_id=current_user.organization_id, order_id=order_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found for this order")
    
    resp = ReportResponse.model_validate(report)
    if report.generator:
        resp.generated_by_name = report.generator.name
    return resp


@router.get("/{id}", response_model=ReportResponse)
def get_report(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get report details by ID. Tenant isolated.
    """
    report = report_repo.get_by_id(db, org_id=current_user.organization_id, id=id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    resp = ReportResponse.model_validate(report)
    if report.generator:
        resp.generated_by_name = report.generator.name
    return resp


@router.get("/{id}/download")
def download_report_pdf(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Securely download/view PDF file for a report. Enforces tenant isolation. Audits download action.
    """
    report = report_repo.get_by_id(db, org_id=current_user.organization_id, id=id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not storage_service.exists(report.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report PDF file not found in storage")

    pdf_bytes = storage_service.read_file(report.file_path)

    # Log REPORT_DOWNLOADED audit record
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    audit_service.log(
        db,
        org_id=current_user.organization_id,
        action="REPORT_DOWNLOADED",
        entity_type="REPORT",
        entity_id=str(report.id),
        user_id=current_user.id,
        branch_id=current_user.branch_id,
        description=f"Downloaded report PDF {report.report_number}",
        ip_address=client_ip,
        user_agent=user_agent,
        success=True,
        metadata_json={
            "report_number": report.report_number,
            "file_name": report.file_name,
            "checksum": report.checksum,
        },
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{report.file_name}"',
            "Content-Length": str(len(pdf_bytes)),
            "X-Report-Checksum": report.checksum,
        },
    )

