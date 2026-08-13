import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.repositories.audit import audit_repo
from app.core.database import SessionLocal

logger = logging.getLogger("app.services.audit")


class AuditService:
    def log(
        self,
        db: Session,
        *,
        org_id: int,
        action: str,
        entity_type: str,
        entity_id: Optional[Any] = None,
        user_id: Optional[int] = None,
        branch_id: Optional[int] = None,
        event_type: Optional[str] = None,
        description: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        failure_reason: Optional[str] = None,
    ):
        """
        Record a durable, append-only audit trail entry.
        """
        try:
            return audit_repo.create_audit(
                db,
                org_id=org_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                user_id=user_id,
                branch_id=branch_id,
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
        except Exception as e:
            logger.error(f"Failed to record audit log action={action}: {str(e)}", exc_info=True)
            db.rollback()
            # Do not throw to prevent crashing main business transaction if db fail, or handle as needed
            return None


audit_service = AuditService()


def domain_event_audit_listener(payload: Dict[str, Any]) -> None:
    """
    Subscribed domain event listener to convert domain events into durable audit records.
    """
    event_name = payload.get("event")
    org_id = payload.get("organization_id")
    if not event_name or not org_id:
        return

    # Map domain event names to standard audit action and entity
    EVENT_MAP = {
        "patient.created": ("PATIENT_CREATED", "PATIENT"),
        "order.created": ("ORDER_CREATED", "ORDER"),
        "sample.created": ("SAMPLE_CREATED", "SAMPLE"),
        "sample.collected": ("SAMPLE_COLLECTED", "SAMPLE"),
        "sample.processing_started": ("SAMPLE_PROCESSING_STARTED", "SAMPLE"),
        "sample.completed": ("SAMPLE_COMPLETED", "SAMPLE"),
        "sample.rejected": ("SAMPLE_REJECTED", "SAMPLE"),
        "result.entered": ("RESULT_SUBMITTED", "RESULT"),
        "result.returned_for_correction": ("RESULT_RETURNED_FOR_CORRECTION", "RESULT"),
        "result.verified": ("RESULT_APPROVED", "RESULT"),
        "order.verified": ("ORDER_VERIFIED", "ORDER"),
        "report.generated": ("REPORT_GENERATED", "REPORT"),
        "report.available": ("REPORT_AVAILABLE", "REPORT"),
    }

    if event_name in EVENT_MAP:
        action, entity_type = EVENT_MAP[event_name]
        entity_id = payload.get("entity_id") or payload.get("order_id") or payload.get("sample_id") or payload.get("patient_id") or payload.get("report_id")
        user_id = payload.get("user_id") or payload.get("created_by") or payload.get("verified_by")

        # Extract old and new values if provided
        old_values = payload.get("old_values")
        new_values = payload.get("new_values")
        description = payload.get("description") or f"Domain event triggered: {event_name}"

        db = SessionLocal()
        try:
            audit_service.log(
                db,
                org_id=org_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                event_type=event_name,
                description=description,
                old_values=old_values,
                new_values=new_values,
                metadata_json={k: v for k, v in payload.items() if k not in ["old_values", "new_values", "event", "organization_id", "user_id"]},
            )
        finally:
            db.close()
