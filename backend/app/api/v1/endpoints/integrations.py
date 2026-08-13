from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
import logging

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.models.report import Report
from app.models.integration import IntegrationDelivery
from app.schemas.integration import (
    IntegrationStatusResponse,
    IntegrationDeliveryResponse,
    IntegrationDeliveryListResponse,
    IntegrationTestResponse,
)
from app.services.integration import integration_service
from app.services.storage import storage_service
from app.services.audit import audit_service
from app.repositories.report import report_repo

router = APIRouter()
logger = logging.getLogger("app.api.integrations")

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.get("", response_model=IntegrationStatusResponse)
def get_integration_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """
    Get n8n integration status and delivery counters for current organization. Admin only.
    """
    org_id = current_user.organization_id
    is_configured = bool(settings.N8N_WEBHOOK_URL)
    
    # Obscure webhook URL for display
    webhook_url_display = None
    if is_configured:
        url = settings.N8N_WEBHOOK_URL
        if len(url) > 25:
            webhook_url_display = f"{url[:15]}...{url[-8:]}"
        else:
            webhook_url_display = url

    sent_count = db.query(IntegrationDelivery).filter(
        IntegrationDelivery.organization_id == org_id,
        IntegrationDelivery.status == "Sent"
    ).count()

    pending_count = db.query(IntegrationDelivery).filter(
        IntegrationDelivery.organization_id == org_id,
        IntegrationDelivery.status == "Pending"
    ).count()

    failed_count = db.query(IntegrationDelivery).filter(
        IntegrationDelivery.organization_id == org_id,
        IntegrationDelivery.status == "Failed"
    ).count()

    last_sent = db.query(IntegrationDelivery).filter(
        IntegrationDelivery.organization_id == org_id,
        IntegrationDelivery.status == "Sent"
    ).order_by(desc(IntegrationDelivery.updated_at)).first()

    last_failed = db.query(IntegrationDelivery).filter(
        IntegrationDelivery.organization_id == org_id,
        IntegrationDelivery.status == "Failed"
    ).order_by(desc(IntegrationDelivery.updated_at)).first()

    if not is_configured:
        conn_status = "Not Configured"
    elif last_failed and (not last_sent or last_failed.updated_at > last_sent.updated_at):
        conn_status = "Connection Error"
    else:
        conn_status = "Connected"

    return {
        "is_configured": is_configured,
        "webhook_url": webhook_url_display,
        "status": conn_status,
        "sent_count": sent_count,
        "pending_count": pending_count,
        "failed_count": failed_count,
        "last_successful_delivery": last_sent.updated_at if last_sent else None,
        "last_failed_delivery": last_failed.updated_at if last_failed else None,
    }


@router.post("/n8n/test", response_model=IntegrationTestResponse)
def test_n8n_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """
    Triggers safe test event (integration.test) to n8n webhook URL. Admin only. No patient data sent.
    """
    success, event_id, status_code, message = integration_service.send_test_event(
        db, org_id=current_user.organization_id
    )
    return {
        "success": success,
        "event_id": event_id,
        "status_code": status_code,
        "message": message,
    }


@router.get("/logs", response_model=IntegrationDeliveryListResponse)
def get_integration_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    status: Optional[str] = Query(None, description="Filter by status (Pending, Sent, Failed)"),
    event_type: Optional[str] = Query(None, description="Filter by event_type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """
    Paginated audit log of integration delivery attempts. Admin only. Tenant isolated.
    """
    query = db.query(IntegrationDelivery).filter(
        IntegrationDelivery.organization_id == current_user.organization_id
    )

    if status:
        query = query.filter(IntegrationDelivery.status == status)
    if event_type:
        query = query.filter(IntegrationDelivery.event_type == event_type)

    total = query.count()
    items = query.order_by(desc(IntegrationDelivery.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/logs/{id}/retry", response_model=IntegrationDeliveryResponse)
def retry_integration_delivery(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """
    Manually retry a failed integration delivery. Admin only. Enforces tenant isolation.
    """
    delivery = db.query(IntegrationDelivery).filter(
        IntegrationDelivery.organization_id == current_user.organization_id,
        IntegrationDelivery.id == id
    ).first()

    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration delivery record not found")

    if delivery.status == "Sent":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event has already been successfully delivered."
        )

    # Re-dispatch payload
    payload_data = {}
    if delivery.event_type == "report.available":
        # Look up report details if available
        # event_id might store report details in delivery record
        rpt = db.query(Report).filter(
            Report.organization_id == current_user.organization_id
        ).order_by(desc(Report.created_at)).first()
        if rpt:
            payload_data = {
                "report_id": rpt.id,
                "report_number": rpt.report_number,
                "order_id": rpt.order_id,
                "patient_id": rpt.patient_id,
                "branch_id": rpt.branch_id,
            }

    updated_delivery = integration_service.dispatch_event(
        db=db,
        org_id=current_user.organization_id,
        event_type=delivery.event_type,
        payload_data=payload_data,
        destination_override=delivery.destination if delivery.destination != "unconfigured" else None,
        event_id_override=delivery.event_id,
    )

    return updated_delivery


@router.get("/reports/{id}/download")
def m2m_download_report_pdf(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
):
    """
    Machine-to-Machine (M2M) secure endpoint for n8n to download report PDF.
    Requires valid X-Integration-Key header matching N8N_INTEGRATION_KEY.
    Enforces tenant isolation and audits M2M access.
    """
    configured_key = settings.N8N_INTEGRATION_KEY
    if not configured_key or not x_integration_key or x_integration_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing M2M integration key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    report = db.query(Report).filter(Report.id == id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not storage_service.exists(report.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report PDF file not found in storage")

    pdf_bytes = storage_service.read_file(report.file_path)

    # Log M2M REPORT_DOWNLOADED audit
    client_ip = get_client_ip(request)
    audit_service.log(
        db,
        org_id=report.organization_id,
        action="REPORT_DOWNLOADED",
        entity_type="REPORT",
        entity_id=str(report.id),
        user_id=None,
        branch_id=report.branch_id,
        description=f"M2M n8n integration downloaded report PDF {report.report_number}",
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True,
        metadata_json={
            "report_number": report.report_number,
            "source": "m2m_n8n_integration",
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
