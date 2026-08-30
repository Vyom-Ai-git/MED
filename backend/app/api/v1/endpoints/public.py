from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from app.models.report import Report
from app.services.storage import storage_service
from app.services.audit import audit_service

router = APIRouter()
logger = logging.getLogger("app.api.public")


def _mask_name(first_name: str, last_name: str) -> str:
    """Show first name + last initial only, for anonymous QR scans."""
    first = (first_name or "").strip()
    last = (last_name or "").strip()
    last_initial = f" {last[0]}." if last else ""
    return f"{first}{last_initial}".strip() or "Patient"


@router.get("/reports/verify/{token}")
def verify_report_authenticity(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Public, no-login authenticity check for a report's QR code.
    Deliberately returns only enough to confirm the report is genuine —
    no PDF, no phone number, no full patient name.
    """
    report = db.query(Report).filter(Report.secure_token == token).first()
    if not report:
        return {"valid": False, "reason": "not_found"}

    if report.secure_token_expires_at:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        exp = report.secure_token_expires_at.replace(tzinfo=None)
        if now > exp:
            return {"valid": False, "reason": "expired"}

    patient = report.patient
    organization = report.organization

    return {
        "valid": True,
        "report_number": report.report_number,
        "status": report.status,
        "organization_name": organization.name if organization else "Vyoma Diagnostics",
        "patient_display_name": _mask_name(
            patient.first_name if patient else "", patient.last_name if patient else ""
        ),
        "generated_at": report.generated_at,
        "verification_code": token[:10].upper(),
    }

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.get("/reports/access/{token}")
def patient_access_report_pdf(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public, secure, token-authenticated endpoint for patient report access.
    Validates token presence and expiration. Audits public patient download.
    """
    report = db.query(Report).filter(Report.secure_token == token).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired secure access token"
        )

    if report.secure_token_expires_at:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        exp = report.secure_token_expires_at.replace(tzinfo=None)
        if now > exp:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Secure report access token has expired"
            )

    if not storage_service.exists(report.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file unavailable in storage"
        )

    pdf_bytes = storage_service.read_file(report.file_path)

    client_ip = get_client_ip(request)
    audit_service.log(
        db,
        org_id=report.organization_id,
        action="PATIENT_REPORT_ACCESS",
        entity_type="REPORT",
        entity_id=str(report.id),
        user_id=None,
        branch_id=report.branch_id,
        description=f"Patient accessed report PDF {report.report_number} via secure token",
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        success=True,
        metadata_json={
            "report_number": report.report_number,
            "access_method": "public_secure_token",
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
