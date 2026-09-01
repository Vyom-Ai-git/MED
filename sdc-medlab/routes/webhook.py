from __future__ import annotations

import hmac
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from services.conversation import normalize_message, process_normalized_message
from services.labos_client import LabOSConfigError
from services.labos_workflow import LabOSWorkflowService
from services.reports import ReportService


logger = logging.getLogger(__name__)

webhook_bp = Blueprint("webhook", __name__)
workflow_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="medlab-workflow")


def _config():
    return current_app.config["APP_CONFIG"]


def _store():
    return current_app.config["STORE"]


def _whatsapp():
    return current_app.config["WHATSAPP"]


def _gemini():
    return current_app.config["GEMINI"]


def _labos():
    return current_app.config["LABOS"]


def _labos_workflow() -> LabOSWorkflowService:
    return current_app.config["LABOS_WORKFLOW"]


def _run_in_app(app, callback, *args) -> None:
    """Restore Flask context inside a background worker."""
    with app.app_context():
        callback(*args)


def _submit(callback, *args) -> None:
    app = current_app._get_current_object()
    if current_app.testing:
        callback(*args)
    else:
        workflow_executor.submit(_run_in_app, app, callback, *args)


@webhook_bp.get("/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode", "")
    token = request.args.get("hub.verify_token", "")
    challenge = request.args.get("hub.challenge", "")
    if mode == "subscribe" and token == _config().meta_verify_token:
        return challenge, 200
    return "Forbidden", 403


def _iter_messages(payload: dict[str, Any]):
    if payload.get("object") != "whatsapp_business_account":
        return
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            for status in value.get("statuses", []) or []:
                yield ("status", value, status)
            for message in value.get("messages", []) or []:
                yield ("message", value, message)


def _normalized_signature(signature: str | None) -> str:
    if not signature:
        return ""
    signature = signature.strip()
    if signature.startswith("sha256="):
        signature = signature.split("=", 1)[1]
    return signature


def _verify_labos_signature(raw_body: bytes, signature: str | None) -> bool:
    secret = _config().labos_webhook_secret
    if not secret:
        raise LabOSConfigError("LABOS_WEBHOOK_SECRET is not configured")
    candidate = _normalized_signature(signature)
    if not candidate:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, candidate)


@webhook_bp.post("/webhook")
def incoming_webhook():
    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({"status": "ok"})

    for kind, value, item in _iter_messages(payload) or []:
        if kind == "status":
            _store().log_event(
                "WEBHOOK_RECEIVED",
                component="webhook",
                status=item.get("status"),
                phone=item.get("recipient_id"),
                report_id=item.get("id"),
            )
            continue
        normalized = normalize_message(value, item)
        if current_app.testing:
            process_normalized_message(_store(), _whatsapp(), _gemini(), normalized)
        else:
            _submit(_labos_workflow().process_whatsapp_message, normalized)

    if current_app.testing:
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "accepted"}), 202


@webhook_bp.post("/api/reports")
def ingest_report():
    config = _config()
    api_key = request.headers.get("X-API-Key", "")
    if not config.report_ingest_api_key or api_key != config.report_ingest_api_key:
        return jsonify({"error": "unauthorized"}), 401

    form = request.form
    file_storage = request.files.get("pdf_file")
    if file_storage is None:
        return jsonify({"error": "pdf_file is required"}), 400

    phone = (form.get("phone") or "").strip()
    patient_id = (form.get("patient_id") or "").strip()
    report_id = (form.get("report_id") or "").strip()
    report_type = (form.get("report_type") or "lab_report").strip()
    report_date = (form.get("report_date") or "").strip()
    pdf_url = (form.get("pdf_url") or "").strip() or None
    report_uuid = (form.get("report_uuid") or "").strip() or None

    if not phone or not report_id:
        return jsonify({"error": "phone and report_id are required"}), 400
    if not report_date:
        return jsonify({"error": "report_date is required"}), 400

    file_bytes = file_storage.read()
    if not file_bytes:
        return jsonify({"error": "empty pdf_file"}), 400

    try:
        report_service = ReportService(_store(), _whatsapp(), _gemini(), config)
        report = report_service.ingest_report(
            phone=phone,
            patient_id=patient_id,
            report_id=report_id,
            report_type=report_type,
            report_date=report_date,
            file_bytes=file_bytes,
            filename=file_storage.filename or f"{report_id}.pdf",
            pdf_url=pdf_url,
            report_uuid=report_uuid,
        )
        public_pdf_url = pdf_url if pdf_url and pdf_url.startswith("https://") else None
        report_service.send_report_ready(
            phone,
            document_url=public_pdf_url,
            filename=file_storage.filename or f"{report_id}.pdf",
        )
        _store().log_event("REPORT_SENT", phone=phone, report_id=report_id, component="whatsapp", status="sent")
        return jsonify({"status": "ok", "report_id": report["report_id"], "report_uuid": report["report_uuid"]}), 201
    except FileExistsError:
        _store().log_event("REPORT_DUPLICATE", phone=phone, report_id=report_id, component="reports", status="duplicate")
        return jsonify({"error": "duplicate report"}), 409
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Report intake failed")
        return jsonify({"error": "report intake failed"}), 500


@webhook_bp.post("/api/v1/webhooks/labos")
def labos_webhook():
    raw_body = request.get_data(cache=True) or b""
    signature = request.headers.get("X-Hub-Signature-256") or request.headers.get("X-Vyoma-Signature")
    if not signature:
        return jsonify({"error": "missing signature"}), 401
    try:
        if not _verify_labos_signature(raw_body, signature):
            return jsonify({"error": "invalid signature"}), 403
    except LabOSConfigError as exc:
        return jsonify({"error": str(exc)}), 503

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "malformed json"}), 400

    if payload.get("event_type") == "integration.test":
        return jsonify({"status": "ok", "event_id": payload.get("event_id")}), 200

    try:
        if not current_app.testing:
            _submit(_labos_workflow().process_report_available, payload)
            return jsonify({"status": "accepted"}), 202

        result = _labos_workflow().process_report_available(payload)
        status = result.get("status")
        if status == "duplicate":
            return jsonify({"status": "duplicate", "event_id": result.get("event_id")}), 200
        if status == "waiting_for_labos_api":
            return jsonify(result), 202
        if status == "deferred":
            return jsonify(result), 202
        if status == "processed":
            return jsonify(result), 200
        return jsonify(result), 500
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("LabOS webhook processing failed")
        return jsonify({"error": "labos webhook processing failed"}), 500
