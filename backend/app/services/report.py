import logging
import datetime
import secrets
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.report import Report
from app.models.order import Order
from app.models.sample import Sample, Result
from app.models.patient import Patient
from app.models.test import Test, TestParameter
from app.models.user import User
from app.services.storage import storage_service
from app.services.pdf_generator import pdf_generator
from app.core.events import dispatch
from app.core.config import settings

logger = logging.getLogger("app.services.report")

class ReportService:
    def generate_report_for_order(
        self, db: Session, order_id: int, org_id: int, user_id: Optional[int] = None
    ) -> Report:
        """
        Generates PDF report for an order.
        Validates that order.status == 'Verified' and all required results are 'Verified'.
        Idempotent: if report already exists for version=1, returns existing report.
        Emits report.generated and report.available events.
        """
        # 1. Fetch Order and validate
        order = db.query(Order).filter(Order.organization_id == org_id, Order.id == order_id).first()
        if not order:
            raise ValueError(f"Order ID {order_id} not found")

        # Idempotency check: if report already exists, return existing report
        existing_rpt = db.query(Report).filter(
            Report.organization_id == org_id,
            Report.order_id == order.id,
            Report.version == 1
        ).first()
        if existing_rpt:
            logger.info(f"Report already exists for Order {order.order_number}: {existing_rpt.report_number}")
            return existing_rpt

        # Validate order status
        if order.status != "Verified":
            raise ValueError(f"Cannot generate report. Order {order.order_number} has status '{order.status}'. Only Verified orders can generate reports.")

        # Validate all samples & results for this order
        samples = db.query(Sample).filter(Sample.organization_id == org_id, Sample.order_id == order.id).all()
        if not samples:
            raise ValueError(f"No samples found for Order {order.order_number}")

        sample_ids = [s.id for s in samples]
        results = db.query(Result).filter(Result.organization_id == org_id, Result.sample_id.in_(sample_ids)).all()

        if not results:
            raise ValueError(f"No results recorded for Order {order.order_number}")

        # Ensure every result is Verified
        unverified = [r for r in results if r.status != "Verified"]
        if unverified:
            raise ValueError(f"Cannot generate report. Order has {len(unverified)} unverified results.")

        # 2. Prepare data payload for PDF generator
        patient = order.patient
        primary_sample = samples[0]

        # Calculate patient age
        age_str = "N/A"
        if patient and patient.date_of_birth:
            today = datetime.date.today()
            age_years = today.year - patient.date_of_birth.year - ((today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day))
            age_str = f"{age_years} YRS"

        has_critical = any(r.critical_flag for r in results)

        # Group results by test
        tests_dict: Dict[int, Dict[str, Any]] = {}
        for r in results:
            if r.test_id not in tests_dict:
                t_obj = db.query(Test).filter(Test.id == r.test_id).first()
                tests_dict[r.test_id] = {
                    "test_name": t_obj.name if t_obj else f"Test #{r.test_id}",
                    "test_code": t_obj.code if t_obj else "",
                    "results": []
                }
            
            p_obj = r.parameter
            tests_dict[r.test_id]["results"].append({
                "parameter_name": p_obj.name if p_obj else f"Param #{r.parameter_id}",
                "raw_value": r.raw_value,
                "unit": r.unit,
                "reference_low": float(r.reference_low) if r.reference_low is not None else None,
                "reference_high": float(r.reference_high) if r.reference_high is not None else None,
                "abnormal_flag": r.abnormal_flag,
                "critical_flag": r.critical_flag,
            })

        # Fetch verifier name
        verifier_name = "Authorized Laboratory Reviewer"
        verified_at_str = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y, %H:%M UTC")
        if results[0].verified_by:
            verifier_user = db.query(User).filter(User.id == results[0].verified_by).first()
            if verifier_user:
                verifier_name = f"{verifier_user.name} ({verifier_user.role.capitalize()})"
        if results[0].verified_at:
            verified_at_str = results[0].verified_at.strftime("%d %b %Y, %H:%M UTC")

        # Generate unique report number
        count = db.query(Report).filter(Report.organization_id == org_id).count() + 1
        year = datetime.datetime.now().year
        report_number = f"RPT-{year}-{count:05d}"

        # Mint a verification token up front so the PDF can carry a QR code
        # that resolves to a public, no-login verification page.
        verify_token = secrets.token_urlsafe(24)
        verify_expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=settings.REPORT_VERIFY_TOKEN_DAYS
        )
        verification_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/verify/{verify_token}"

        report_data = {
            "organization_name": order.organization.name if order.organization else "Vyoma Diagnostics",
            "report": {
                "report_number": report_number,
            },
            "patient": {
                "first_name": patient.first_name if patient else "",
                "last_name": patient.last_name if patient else "",
                "patient_id": patient.patient_id if patient else "",
                "gender": patient.gender.capitalize() if patient else "",
                "age": age_str,
                "phone": patient.phone if patient else "",
            },
            "order": {
                "order_number": order.order_number,
                "created_at": order.created_at.strftime("%d %b %Y"),
            },
            "sample": {
                "sample_identifier": primary_sample.sample_identifier,
                "sample_type": primary_sample.sample_type,
                "collected_at": primary_sample.collected_at.strftime("%d %b %Y, %H:%M") if primary_sample.collected_at else "N/A",
            },
            "has_critical": has_critical,
            "tests": list(tests_dict.values()),
            "verified_by_name": verifier_name,
            "verified_at": verified_at_str,
            "verification_url": verification_url,
            "verification_code": verify_token[:10].upper(),
        }

        # 3. Render PDF
        pdf_bytes = pdf_generator.generate_pdf(report_data)

        # 4. Save file to storage
        relative_path = f"reports/{org_id}/{year}/{report_number}.pdf"
        file_path, checksum, file_size = storage_service.save_file(pdf_bytes, relative_path)

        now = datetime.datetime.now(datetime.timezone.utc)
        report_record = Report(
            organization_id=org_id,
            branch_id=order.branch_id,
            order_id=order.id,
            patient_id=order.patient_id,
            report_number=report_number,
            status="Available",
            version=1,
            file_name=f"{report_number}.pdf",
            file_path=file_path,
            file_size=file_size,
            mime_type="application/pdf",
            checksum=checksum,
            generated_at=now,
            generated_by=user_id,
            secure_token=verify_token,
            secure_token_expires_at=verify_expires_at,
        )

        try:
            db.add(report_record)
            db.commit()
            db.refresh(report_record)
        except Exception as e:
            db.rollback()
            storage_service.delete_file(file_path)
            logger.error(f"Failed to save Report metadata: {e}")
            raise ValueError(f"Report generation failed: {str(e)}") from e

        # Emit events
        dispatch("report.generated", {
            "report_id": report_record.id,
            "report_number": report_record.report_number,
            "order_id": order.id,
            "patient_id": order.patient_id,
            "organization_id": org_id,
        })
        dispatch("report.available", {
            "report_id": report_record.id,
            "report_number": report_record.report_number,
            "order_id": order.id,
            "patient_id": order.patient_id,
            "organization_id": org_id,
        })

        return report_record


report_service = ReportService()
