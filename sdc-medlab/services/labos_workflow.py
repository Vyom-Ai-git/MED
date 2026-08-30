from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from uuid import uuid4

from services.labos_client import LabOSClient, LabOSClientError, LabOSConfigError, LabOSContractNotReady
from services.report_access import ReportAccessService
from services.reports import ReportService, build_labos_report_buttons, report_ready_message, fallback_summary_message


logger = logging.getLogger(__name__)


class LabOSWorkflowService:
    def __init__(self, store, whatsapp, gemini, labos_client, config):
        self.store = store
        self.whatsapp = whatsapp
        self.gemini = gemini
        self.labos = labos_client
        self.config = config
        self.report_service = ReportService(store, whatsapp, gemini, config)
        self.report_access = ReportAccessService(config, labos_client)

    def process_whatsapp_message(self, message: dict[str, str]) -> None:
        """Run the native WhatsApp conversation workflow in Flask."""
        from services.conversation import process_normalized_message

        try:
            process_normalized_message(self.store, self.whatsapp, self.gemini, message, self.labos)
        except Exception:
            logger.exception("Native WhatsApp workflow failed")
            phone = message.get("phone")
            if phone:
                self.whatsapp.send_text(phone, LabOSClient.DELAY_MESSAGE)
                self.store.log_event(
                    "WORKFLOW_FAILED",
                    phone=phone,
                    component="native_workflow",
                    status="fallback",
                    error_code="NATIVE_WORKFLOW_ERROR",
                )

    def _report_cache_path(self, report_id: str, filename: str) -> Path:
        cache_dir = Path(self.config.report_storage_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{report_id}-{filename}"

    def _event_payload(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        required = ["event_id", "event_type", "report_id", "patient_id", "report_number"]
        missing = [field for field in required if not raw_event.get(field)]
        if missing:
            raise ValueError(f"Missing required field(s): {', '.join(missing)}")
        if raw_event.get("event_type") != "report.available":
            raise ValueError("Unsupported event type")
        return raw_event

    def _resolve_phone(self, event: dict[str, Any], report_meta: dict[str, Any] | None) -> str | None:
        for source in (event, report_meta or {}):
            phone = source.get("patient_phone") or source.get("phone") or source.get("whatsapp_number")
            if phone:
                return phone
        try:
            patient = self.labos.get_patient(event["patient_id"])
            return patient.get("phone") or patient.get("whatsapp_number")
        except LabOSContractNotReady:
            return None
        except Exception:
            logger.exception("Patient lookup failed")
            return None

    def process_report_available(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        event = self._event_payload(raw_event)
        self.report_access.labos_client = self.labos
        event_id = event["event_id"]
        if not self.store.insert_labos_event(
            {
                "event_id": event_id,
                "event_type": event["event_type"],
                "status": "received",
                "received_at": datetime.now(timezone.utc),
                "processed_at": None,
                "attempt_count": 1,
                "error": None,
            }
        ):
            self.store.update_labos_event(event_id, {"attempt_count": 2})
            self.store.log_event("REPORT_DUPLICATE", report_id=event["report_id"], component="labos", status="duplicate")
            return {"status": "duplicate", "event_id": event_id}

        self.store.update_labos_event(event_id, {"status": "validated"})
        report_meta: dict[str, Any] | None = None
        try:
            try:
                report_meta = self.labos.get_report_metadata(event["report_id"])
                report_meta = LabOSClient.normalize_report_payload(report_meta)
            except LabOSContractNotReady:
                report_meta = None
            if report_meta is not None and hasattr(self.labos, "get_verified_results"):
                try:
                    verified = self.labos.get_verified_results(event["report_id"])
                    report_meta["structured_result"] = LabOSClient.normalize_report_payload(verified)
                except LabOSClientError:
                    logger.warning("Verified result retrieval unavailable for %s", event["report_id"])
            phone = self._resolve_phone(event, report_meta)
            if not phone:
                self.store.update_labos_event(event_id, {"status": "waiting_for_labos_api", "error": "WAITING_FOR_LABOS_API"})
                self.store.log_event("WAITING_FOR_LABOS_API", report_id=event["report_id"], component="labos", status="pending")
                return {"status": "waiting_for_labos_api", "event_id": event_id}

            download = self.labos.download_report(event["report_id"])
            filename = f"{event['report_number']}.pdf"
            report_doc = self.report_service.cache_labos_report(
                phone=phone,
                patient_id=event["patient_id"],
                report_id=event["report_id"],
                report_number=event["report_number"],
                file_bytes=download.content,
                filename=filename,
                organization_id=event.get("organization_id"),
                branch_id=event.get("branch_id"),
                order_id=event.get("order_id"),
                structured_result=(report_meta or {}).get("structured_result") if report_meta else None,
                critical_flag=bool((report_meta or {}).get("critical_flag")),
                patient_name=(report_meta or {}).get("patient_name"),
                source_event_id=event_id,
            )
            self.store.update_labos_event(event_id, {"status": "processing"})
            document_url = None
            if hasattr(self.labos, "get_secure_link"):
                document_url = self.report_access.get_patient_facing_url(report_doc)
            self.report_service.send_labos_report_ready(
                phone,
                report_doc.get("patient_name"),
                event["report_number"],
                document_url=document_url,
                filename=filename,
            )
            self.store.set_state(
                phone,
                "report_available",
                language="en",
                active_report_id=report_doc["report_id"],
                selected_option="report_available",
            )
            self.store.update_labos_event(event_id, {"status": "processed", "processed_at": datetime.now(timezone.utc)})
            self.store.log_event("REPORT_SENT", phone=phone, report_id=event["report_id"], component="whatsapp", status="sent")
            return {"status": "processed", "event_id": event_id, "phone": phone}
        except (LabOSClientError, LabOSConfigError) as exc:
            phone = self._resolve_phone(event, report_meta)
            delay_message = getattr(self.labos, "DELAY_MESSAGE", LabOSClient.DELAY_MESSAGE)
            if phone:
                self.whatsapp.send_text(phone, delay_message)
            self.store.update_labos_event(event_id, {"status": "deferred", "error": str(exc)})
            self.store.log_event("REPORT_DEFERRED", report_id=event["report_id"], component="labos", status="retryable", error_code="LABOS_UNAVAILABLE")
            return {"status": "deferred", "event_id": event_id, "message": delay_message}
        except Exception as exc:
            logger.exception("LabOS report processing failed")
            self.store.update_labos_event(event_id, {"status": "failed", "error": str(exc)})
            self.store.log_event("REPORT_FAILED", report_id=event["report_id"], component="labos", status="failed", error_code="LABOS_WORKFLOW_ERROR")
            return {"status": "failed", "event_id": event_id}
