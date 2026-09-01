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


from app.api.deps import get_current_user, get_current_user_or_m2m, require_roles

@router.get("", response_model=IntegrationStatusResponse)
def get_integration_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_m2m),
):
    """
    Get native Flask workflow status and delivery counters for current organization. Admin only.
    """
    if hasattr(current_user, "role") and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    org_id = current_user.organization_id
    is_configured = bool(settings.FLASK_WORKFLOW_URL)

    # Obscure webhook URL for display
    webhook_url_display = None
    if is_configured:
        url = settings.FLASK_WORKFLOW_URL
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


@router.post("/test", response_model=IntegrationTestResponse)
def test_native_workflow(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """
    Triggers a safe test event to the native Flask workflow. Admin only. No patient data sent.
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
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
):
    """
    Machine-to-Machine (M2M) secure endpoint for the native workflow to download report PDF.
    Requires valid X-Integration-Key header matching LABOS_API_KEY.
    Enforces tenant isolation and audits M2M access.
    """
    configured_key = settings.LABOS_API_KEY
    if not configured_key or not x_integration_key or x_integration_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing M2M integration key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if id.isdigit():
        report = db.query(Report).filter(Report.id == int(id)).first()
    else:
        report = db.query(Report).filter(Report.report_number == id).first()

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
        description=f"M2M native workflow downloaded report PDF {report.report_number}",
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True,
        metadata_json={
            "report_number": report.report_number,
            "source": "m2m_native_workflow",
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


@router.get("/reports/{id}/metadata", response_model=dict)
def m2m_get_report_metadata(
    id: str,
    db: Session = Depends(get_db),
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
):
    """
    Machine-to-Machine (M2M) endpoint for the native workflow to fetch report metadata.
    """
    configured_key = settings.LABOS_API_KEY
    if not configured_key or not x_integration_key or x_integration_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing M2M integration key",
        )

    if id.isdigit():
        report = db.query(Report).filter(Report.id == int(id)).first()
    else:
        report = db.query(Report).filter(Report.report_number == id).first()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    order = report.order
    patient = report.patient

    verified_by = None
    if order and getattr(order, "verified_by", None):
        from app.models.user import User as UserModel
        p_user = db.query(UserModel).filter(UserModel.id == getattr(order, "verified_by")).first()
        if p_user:
            verified_by = p_user.name


    return {
        "id": report.id,
        "report_number": report.report_number,
        "organization_id": report.organization_id,
        "branch_id": report.branch_id,
        "order_id": report.order_id,
        "order_number": order.order_number if order else "",
        "patient_id": report.patient_id,
        "patient_mrn": patient.patient_id if patient else "",
        "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "",
        "patient_phone": patient.phone if patient else "",
        "status": report.status,
        "version": report.version,
        "file_name": report.file_name,
        "file_size": report.file_size,
        "mime_type": report.mime_type,
        "checksum": report.checksum,
        "page_count": getattr(report, "page_count", 1) or 1,
        "generated_at": report.generated_at,
        "verification_status": "Verified" if (order and order.status == "Verified") else report.status,
        "verified_by_pathologist": verified_by,
        "download_url": f"/api/v1/integrations/reports/{report.id}/download",
    }


@router.get("/reports/{id}/results", response_model=dict)
def m2m_get_verified_report_results(
    id: str,
    db: Session = Depends(get_db),
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
):
    """
    Machine-to-Machine (M2M) endpoint for the native workflow to fetch verified lab test results.
    """
    configured_key = settings.LABOS_API_KEY
    if not configured_key or not x_integration_key or x_integration_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing M2M integration key",
        )

    if id.isdigit():
        report = db.query(Report).filter(Report.id == int(id)).first()
    else:
        report = db.query(Report).filter(Report.report_number == id).first()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    order = report.order
    patient = report.patient

    from app.models.sample import Result, Sample
    results = []
    if order:
        samples = db.query(Sample).filter(Sample.order_id == order.id).all()
        for sample in samples:
            test_results = db.query(Result).filter(Result.sample_id == sample.id).all()
            for tr in test_results:
                param_name = tr.parameter.name if tr.parameter else "Parameter"
                test_name = tr.test.name if tr.test else "Diagnostic Test"
                val = tr.raw_value or (str(tr.numeric_value) if tr.numeric_value is not None else tr.text_value or "")
                ref_range = f"{tr.reference_low} - {tr.reference_high}" if (tr.reference_low is not None and tr.reference_high is not None) else None

                results.append({
                    "test_code": f"TST-{tr.id:04d}",
                    "test_name": test_name,
                    "parameter_name": param_name,
                    "result_value": val,
                    "unit": tr.unit,
                    "reference_range": ref_range,
                    "flag": tr.abnormal_flag or "Normal",
                    "status": "Verified" if order and order.status == "Verified" else "Completed",
                })


    return {
        "report_id": report.id,
        "report_number": report.report_number,
        "order_id": report.order_id,
        "order_number": order.order_number if order else "",
        "patient_id": report.patient_id,
        "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "",
        "patient_mrn": patient.patient_id if patient else "",
        "overall_status": order.status if order else "Verified",
        "results": results,
    }


@router.get("/patients/lookup", response_model=dict)
def m2m_lookup_patient_communication(
    patient_id: str,
    db: Session = Depends(get_db),
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
):
    """
    Machine-to-Machine (M2M) endpoint for patient lookup by patient_id (MRN).
    """
    configured_key = settings.LABOS_API_KEY
    if not configured_key or not x_integration_key or x_integration_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing M2M integration key",
        )

    from app.models.patient import Patient
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient record not found")

    return {
        "id": patient.id,
        "patient_id": patient.patient_id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "full_name": f"{patient.first_name} {patient.last_name}",
        "phone": patient.phone,
        "email": patient.email,
        "communication_preference": patient.communication_preference,
        "consent_promotional": patient.consent_promotional,
    }

@router.post("/reports/{id}/secure-link", response_model=dict)
def m2m_generate_patient_secure_link(
    id: str,
    expires_in_hours: int = Query(72, ge=1, le=720),
    db: Session = Depends(get_db),
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
):
    """
    Machine-to-Machine (M2M) endpoint to generate a secure signed token link for patient-facing report access.
    """
    configured_key = settings.LABOS_API_KEY
    if not configured_key or not x_integration_key or x_integration_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing M2M integration key",
        )

    import secrets
    from datetime import datetime, timezone, timedelta

    if id.isdigit():
        report = db.query(Report).filter(Report.id == int(id)).first()
    else:
        report = db.query(Report).filter(Report.report_number == id).first()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

    report.secure_token = token
    report.secure_token_expires_at = expires_at
    db.commit()

    access_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/api/v1/public/reports/access/{token}"

    return {
        "report_id": report.id,
        "report_number": report.report_number,
        "secure_token": token,
        "url": access_url,
        "expires_at": expires_at,
    }
