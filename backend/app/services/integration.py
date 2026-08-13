import logging
import uuid
import hmac
import hashlib
import json
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.integration import IntegrationDelivery
from app.services.audit import audit_service

logger = logging.getLogger("app.services.integration")

def compute_hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """Computes HMAC-SHA256 signature for payload using secret."""
    if not secret:
        return ""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

def verify_hmac_signature(payload_bytes: bytes, secret: str, signature_header: str) -> bool:
    """Validates an incoming HMAC-SHA256 signature against payload and secret."""
    if not secret or not signature_header:
        return False
    clean_sig = signature_header.replace("sha256=", "").strip()
    expected_sig = compute_hmac_signature(payload_bytes, secret)
    return hmac.compare_digest(clean_sig, expected_sig)


class IntegrationService:
    def dispatch_event(
        self,
        db: Session,
        org_id: int,
        event_type: str,
        payload_data: Dict[str, Any],
        destination_override: Optional[str] = None,
        event_id_override: Optional[str] = None,
    ) -> IntegrationDelivery:
        """
        Dispatches an outbound integration event to n8n webhook.
        Handles idempotency, HMAC signing, HTTP delivery, retries, and audit logging.
        """
        destination = destination_override or settings.N8N_WEBHOOK_URL
        event_id = event_id_override or f"evt_{uuid.uuid4().hex}"

        # 1. Idempotency Check: if event_id already delivered, do not send again automatically
        existing_delivery = db.query(IntegrationDelivery).filter(
            IntegrationDelivery.organization_id == org_id,
            IntegrationDelivery.event_id == event_id
        ).first()

        if existing_delivery and existing_delivery.status == "Sent":
            logger.info(f"Event {event_id} has already been successfully delivered. Skipping duplicate dispatch.")
            return existing_delivery

        # Create or update delivery record
        now = datetime.now(timezone.utc)
        if existing_delivery:
            delivery = existing_delivery
            delivery.attempts += 1
            delivery.last_attempt_at = now
            delivery.updated_at = now
        else:
            delivery = IntegrationDelivery(
                organization_id=org_id,
                event_id=event_id,
                event_type=event_type,
                destination=destination or "unconfigured",
                status="Pending",
                attempts=1,
                last_attempt_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(delivery)
            db.commit()
            db.refresh(delivery)

        # If webhook URL is missing, mark as failed and return
        if not destination:
            delivery.status = "Failed"
            delivery.error_message = "n8n Webhook URL is not configured (N8N_WEBHOOK_URL is empty)"
            db.commit()

            audit_service.log(
                db,
                org_id=org_id,
                action="INTEGRATION_FAILED",
                entity_type="INTEGRATION",
                entity_id=str(delivery.id),
                description=f"Integration delivery failed: N8N_WEBHOOK_URL missing for event {event_id}",
                success=False,
                metadata_json={
                    "event_id": event_id,
                    "event_type": event_type,
                    "destination": delivery.destination,
                    "error": delivery.error_message,
                }
            )
            return delivery

        # Construct full standardized JSON event payload
        event_payload = {
            "event_id": event_id,
            "event_type": event_type,
            "event_version": "1.0",
            "timestamp": now.isoformat(),
            "organization_id": org_id,
            "branch_id": payload_data.get("branch_id"),
            "report_id": payload_data.get("report_id"),
            "report_number": payload_data.get("report_number"),
            "order_id": payload_data.get("order_id"),
            "patient_id": payload_data.get("patient_id"),
        }

        raw_body = json.dumps(event_payload, separators=(',', ':')).encode("utf-8")
        signature = compute_hmac_signature(raw_body, settings.N8N_WEBHOOK_SECRET)

        headers = {
            "Content-Type": "application/json",
            "X-Vyoma-Signature": f"sha256={signature}" if signature else "",
            "X-Vyoma-Event-ID": event_id,
            "X-Vyoma-Event-Type": event_type,
        }

        # Perform HTTP POST request with retry logic for 5xx/connection errors
        max_attempts = settings.INTEGRATION_MAX_RETRIES
        timeout = settings.INTEGRATION_TIMEOUT_SECONDS

        response_status = None
        last_error = None
        is_success = False

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Attempting n8n webhook POST ({attempt}/{max_attempts}) for event {event_id} -> {destination}")
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(destination, content=raw_body, headers=headers)
                    response_status = resp.status_code

                    # 200 or 202 is considered successful delivery
                    if resp.status_code in (200, 201, 202):
                        is_success = True
                        break
                    elif resp.status_code >= 500:
                        last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                        # Retry on 5xx errors
                        continue
                    else:
                        # 4xx Client error - do not retry repeatedly
                        last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                        break
            except Exception as exc:
                last_error = f"Connection error: {str(exc)}"
                logger.warning(f"Attempt {attempt} failed for event {event_id}: {last_error}")

        delivery.response_status = response_status
        delivery.last_attempt_at = datetime.now(timezone.utc)
        delivery.attempts = attempt if 'attempt' in locals() else delivery.attempts

        if is_success:
            delivery.status = "Sent"
            delivery.error_message = None
            db.commit()

            audit_service.log(
                db,
                org_id=org_id,
                action="INTEGRATION_SENT",
                entity_type="INTEGRATION",
                entity_id=str(delivery.id),
                description=f"Integration event {event_type} ({event_id}) sent successfully to n8n",
                success=True,
                metadata_json={
                    "event_id": event_id,
                    "event_type": event_type,
                    "destination": destination,
                    "response_status": response_status,
                }
            )
        else:
            delivery.status = "Failed"
            delivery.error_message = last_error or "Unknown integration error"
            db.commit()

            audit_service.log(
                db,
                org_id=org_id,
                action="INTEGRATION_FAILED",
                entity_type="INTEGRATION",
                entity_id=str(delivery.id),
                description=f"Integration delivery failed for event {event_id}: {delivery.error_message}",
                success=False,
                metadata_json={
                    "event_id": event_id,
                    "event_type": event_type,
                    "destination": destination,
                    "response_status": response_status,
                    "error": delivery.error_message,
                }
            )

        return delivery

    def send_test_event(self, db: Session, org_id: int) -> Tuple[bool, str, Optional[int], str]:
        """
        Sends a safe integration.test event to n8n without patient data.
        """
        event_id = f"test_{uuid.uuid4().hex}"
        test_payload = {
            "event_id": event_id,
            "event_type": "integration.test",
            "event_version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "organization_id": org_id,
        }

        destination = settings.N8N_WEBHOOK_URL
        if not destination:
            return False, event_id, None, "N8N_WEBHOOK_URL is not configured"

        raw_body = json.dumps(test_payload, separators=(',', ':')).encode("utf-8")
        signature = compute_hmac_signature(raw_body, settings.N8N_WEBHOOK_SECRET)
        headers = {
            "Content-Type": "application/json",
            "X-Vyoma-Signature": f"sha256={signature}" if signature else "",
            "X-Vyoma-Event-ID": event_id,
            "X-Vyoma-Event-Type": "integration.test",
        }

        try:
            with httpx.Client(timeout=settings.INTEGRATION_TIMEOUT_SECONDS) as client:
                resp = client.post(destination, content=raw_body, headers=headers)
                if resp.status_code in (200, 201, 202):
                    return True, event_id, resp.status_code, "n8n test webhook connection successful"
                else:
                    return False, event_id, resp.status_code, f"n8n test returned status {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            return False, event_id, None, f"Connection failed: {str(exc)}"


integration_service = IntegrationService()


def handle_report_available_event(payload: Dict[str, Any]) -> None:
    """
    Event listener callback registered to 'report.available'.
    Runs safely in a separate DB session so clinical flow is never blocked.
    """
    org_id = payload.get("organization_id")
    if not org_id:
        logger.warning("report.available event missing organization_id. Cannot dispatch integration.")
        return

    db = SessionLocal()
    try:
        integration_service.dispatch_event(
            db=db,
            org_id=org_id,
            event_type="report.available",
            payload_data=payload,
        )
    except Exception as e:
        logger.error(f"Error handling report.available integration dispatch: {str(e)}", exc_info=True)
    finally:
        db.close()
