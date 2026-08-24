from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from services.booking_adapters import CustomerCareService
from services.intent import detect_intent
from services.report_access import ReportAccessService
from services.reports import (
    ReportService,
    build_language_buttons,
    safe_report_message,
    normalize_language,
    fallback_summary_message,
)
from services.safety import emergency_message, is_emergency_text, safe_ai_failure_message


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NormalizedMessage:
    message_id: str
    phone: str
    timestamp: str
    type: str
    text: str
    button_id: str
    button_title: str
    media_id: str
    filename: str

    def as_dict(self) -> dict[str, str]:
        return {
            "message_id": self.message_id,
            "phone": self.phone,
            "timestamp": self.timestamp,
            "type": self.type,
            "text": self.text,
            "button_id": self.button_id,
            "button_title": self.button_title,
            "media_id": self.media_id,
            "filename": self.filename,
        }


GLOBAL_COMMANDS = {"menu", "home", "help", "cancel", "stop", "restart"}


def normalize_message(value: dict[str, Any], message: dict[str, Any]) -> dict[str, str]:
    interactive = message.get("interactive") or {}
    button_reply = interactive.get("button_reply") or {}
    list_reply = interactive.get("list_reply") or {}
    message_type = message.get("type", "unknown")
    text = ""
    button_id = ""
    button_title = ""
    media_id = ""
    filename = ""

    if message_type == "text":
        text = (message.get("text") or {}).get("body", "") or ""
    elif message_type == "interactive":
        button_id = button_reply.get("id") or list_reply.get("id") or ""
        button_title = button_reply.get("title") or list_reply.get("title") or ""
        text = button_title or button_id
    elif message_type in {"document", "image", "audio"}:
        media = message.get(message_type) or {}
        media_id = media.get("id", "") or ""
        filename = media.get("filename", "") or ""
        text = message.get("caption", "") or filename
    else:
        text = message.get("text", {}).get("body", "") or ""

    return NormalizedMessage(
        message_id=message.get("id", ""),
        phone=message.get("from") or (value.get("contacts") or [{}])[0].get("wa_id", ""),
        timestamp=message.get("timestamp", "") or str(int(datetime.now(timezone.utc).timestamp())),
        type=message_type,
        text=text,
        button_id=button_id,
        button_title=button_title,
        media_id=media_id,
        filename=filename,
    ).as_dict()


def _text_for_command(msg: dict[str, str]) -> str:
    return (msg.get("button_id") or msg.get("button_title") or msg.get("text") or "").strip().lower()


def _send_main_menu(store, whatsapp, phone: str) -> None:
    whatsapp.send_interactive_buttons(
        phone,
        "Welcome to SDC Labs.\nHow can I help you today?",
        [
            {"id": "analyze_report", "title": "Analyze Report"},
            {"id": "book_test", "title": "Book Test"},
            {"id": "customer_support", "title": "Customer Support"},
        ],
    )
    store.log_event("MENU_SENT", phone=phone, component="conversation", status="sent")


def _send_greeting_menu(store, whatsapp, phone: str) -> None:
    whatsapp.send_interactive_buttons(
        phone,
        "Hello.\nWelcome to SDC Labs.\n\nHow can we help you today?",
        [
            {"id": "consult_doctor", "title": "Consult Doctor"},
            {"id": "book_lab_test", "title": "Book Lab Test"},
            {"id": "customer_care", "title": "Customer Care"},
        ],
    )
    store.log_event("MENU_SENT", phone=phone, component="conversation", status="greeting")


def _send_language_prompt(store, whatsapp, phone: str) -> None:
    whatsapp.send_interactive_buttons(phone, "Please choose your language.", build_language_buttons())
    store.log_event("LANGUAGE_SELECTED", phone=phone, component="conversation", status="prompt")


def _handle_book_test(store, whatsapp, phone: str, text: str) -> None:
    store.set_state(phone, "lab_booking", selected_option=text or "book_lab_test")
    whatsapp.send_text(
        phone,
        "LAB_BOOKING_API_NOT_CONFIGURED\n"
        "Lab booking is ready for LabOS API integration, but live booking availability is not configured yet.",
    )
    store.log_event("BOOKING_STARTED", phone=phone, component="booking", status="adapter_only")


def _handle_consultation(store, whatsapp, phone: str, text: str) -> None:
    store.set_state(phone, "doctor_consultation", selected_option=text or "consult_doctor")
    whatsapp.send_text(
        phone,
        "DOCTOR_BOOKING_API_NOT_CONFIGURED\n"
        "Doctor consultation booking is ready for LabOS API integration, but live availability is not configured yet.",
    )
    store.log_event("BOOKING_STARTED", phone=phone, component="consultation", status="adapter_only")


def _handle_support(store, whatsapp, phone: str, text: str) -> None:
    care = CustomerCareService(store)
    created = care.create_request(phone, text or "Support requested")
    if created:
        store.log_event("SUPPORT_CREATED", phone=phone, component="support", status="created")
        whatsapp.send_text(phone, "Your request has been forwarded to our support team.")
    else:
        whatsapp.send_text(phone, "A support request already exists. Please reply with `restart` to start over.")


def _handle_cached_or_generate_analysis(store, whatsapp, gemini, phone: str, language: str) -> None:
    report_service = ReportService(store, whatsapp, gemini, store.config)
    try:
        result = report_service.analyze_report_for_phone(phone, language)
        report = result.get("report") or result.get("analysis") or store.get_report_by_phone_and_id(phone, store.get_state(phone).get("active_report_id"))
        if result.get("cached"):
            analysis = {
                "summary": report.get("summary_en") if normalize_language(language) == "en" else report.get("summary_ml"),
                "tests": [],
                "key_findings": [],
                "doctor_discussion": [],
                "safety_notice": "⚠️ This AI explanation is for informational purposes only and is not a diagnosis or medical advice. Please discuss your results with a qualified healthcare professional.",
            }
            store.log_event("ANALYSIS_CACHED", phone=phone, report_id=report.get("report_id"), component="reports", status=language)
        else:
            analysis = result["analysis"]
        report_service.send_analysis_result(phone, analysis, language)
    except LookupError:
        whatsapp.send_text(phone, safe_report_message())
    except RuntimeError as exc:
        if str(exc) == emergency_message():
            store.set_state(phone, "emergency_halt", language=language)
            whatsapp.send_text(phone, str(exc))
            store.log_event("EMERGENCY_HALT", phone=phone, component="safety", status="halted")
        else:
            logger.exception("AI analysis failed")
            store.log_event("ANALYSIS_FAILED", phone=phone, component="gemini", status="failed", error_code="AI_ANALYSIS_FAILED")
            whatsapp.send_text(phone, safe_ai_failure_message())
    except Exception:
        logger.exception("AI analysis failed")
        store.log_event("ANALYSIS_FAILED", phone=phone, component="gemini", status="failed", error_code="AI_ANALYSIS_FAILED")
        whatsapp.send_text(phone, safe_ai_failure_message())


def process_normalized_message(store, whatsapp, gemini, msg: dict[str, str]) -> None:
    phone = msg["phone"]
    if not msg["message_id"]:
        return
    if not store.mark_processed_message(msg["message_id"], phone, msg["type"]):
        store.log_event("MESSAGE_DEDUPLICATED", phone=phone, component="webhook", status="duplicate")
        return

    store.log_event(
        "WEBHOOK_RECEIVED",
        phone=phone,
        message_id=msg["message_id"],
        component="webhook",
        status=msg["type"],
        state=store.get_state(phone).get("state"),
    )
    text = (msg.get("text") or "").strip()
    state = store.get_state(phone)
    if store.state_expired(state):
        store.reset_state(phone)
        whatsapp.send_text(phone, "Your previous session has expired. Let's start again.")
        _send_main_menu(store, whatsapp, phone)
        store.log_event("SESSION_EXPIRED", phone=phone, component="conversation", status="expired", state=state.get("state"))
        return

    intent = detect_intent(text, button_id=msg.get("button_id", ""), button_title=msg.get("button_title", ""))
    command = _text_for_command(msg)

    if is_emergency_text(text):
        store.set_state(phone, "emergency_halt", language=state.get("language", "en"), active_report_id=state.get("active_report_id"))
        whatsapp.send_text(phone, emergency_message())
        store.log_event("EMERGENCY_HALT", phone=phone, component="safety", status="halted")
        return

    if intent.intent == "greeting":
        store.reset_state(phone)
        _send_greeting_menu(store, whatsapp, phone)
        return

    if command in GLOBAL_COMMANDS or intent.intent == "menu":
        store.reset_state(phone)
        if command in {"cancel", "stop"}:
            whatsapp.send_text(phone, "Your current flow has been cancelled.")
        _send_main_menu(store, whatsapp, phone)
        return

    if command in {"analyze_report", "analyze_sample_01"} or intent.intent == "report":
        active_report = store.get_state(phone).get("active_report_id")
        latest = store.get_report_by_phone_and_id(phone, active_report) or store.get_latest_report_by_phone(phone)
        if not latest:
            whatsapp.send_text(phone, safe_report_message())
            store.log_event("ANALYSIS_FAILED", phone=phone, component="reports", status="missing_report", error_code="NO_REPORT")
            return
        store.set_state(
            phone,
            "report_language",
            language=state.get("language", "en"),
            active_report_id=latest["report_id"],
            selected_option="report_analyze",
        )
        _send_language_prompt(store, whatsapp, phone)
        return

    if command in {"lang_en", "english", "en"} or intent.intent == "language" and "en" in text.lower():
        store.set_language(phone, "en")
        store.set_state(phone, "analyzing", language="en", active_report_id=state.get("active_report_id"))
        _handle_cached_or_generate_analysis(store, whatsapp, gemini, phone, "en")
        store.set_state(phone, "report_summary", language="en", active_report_id=store.get_state(phone).get("active_report_id"), selected_option="summary")
        return

    if command in {"lang_ml", "malayalam", "ml"} or intent.intent == "language" and ("ml" in text.lower() or "മലയാളം" in text):
        store.set_language(phone, "ml")
        store.set_state(phone, "analyzing", language="ml", active_report_id=state.get("active_report_id"))
        _handle_cached_or_generate_analysis(store, whatsapp, gemini, phone, "ml")
        store.set_state(phone, "report_summary", language="ml", active_report_id=store.get_state(phone).get("active_report_id"), selected_option="summary")
        return

    if command == "view_report":
        report_id = store.get_state(phone).get("active_report_id")
        report = store.get_report_by_phone_and_id(phone, report_id) or store.get_latest_report_by_phone(phone)
        if report:
            access = ReportAccessService(store.config)
            try:
                link = access.get_patient_facing_url(report)
                whatsapp.send_text(phone, f"Your official report link is ready:\n{link}")
            except NotImplementedError:
                whatsapp.send_text(phone, access.describe_unavailable())
        else:
            whatsapp.send_text(phone, safe_report_message())
        return

    if command in {"book_test", "book_lab_test"} or intent.intent == "lab":
        store.set_state(phone, "lab_booking", language=state.get("language", "en"), active_report_id=state.get("active_report_id"), selected_option="book_lab_test")
        _handle_book_test(store, whatsapp, phone, text)
        return

    if command == "consult_doctor" or intent.intent == "doctor":
        store.set_state(phone, "doctor_consultation", language=state.get("language", "en"), active_report_id=state.get("active_report_id"), selected_option="consult_doctor")
        _handle_consultation(store, whatsapp, phone, text)
        return

    if command in {"customer_support", "customer_care"} or intent.intent == "customer_care":
        store.set_state(phone, "support", language=state.get("language", "en"), active_report_id=state.get("active_report_id"))
        _handle_support(store, whatsapp, phone, text)
        return

    if command == "back":
        store.reset_state(phone)
        _send_main_menu(store, whatsapp, phone)
        return

    if state.get("state") in {"booking", "lab_booking"}:
        if command in {"cancel", "stop"}:
            store.reset_state(phone)
            _send_main_menu(store, whatsapp, phone)
            return
        _handle_book_test(store, whatsapp, phone, text)
        return

    if state.get("state") == "doctor_consultation":
        _handle_consultation(store, whatsapp, phone, text)
        return

    if state.get("state") == "support":
        _handle_support(store, whatsapp, phone, text)
        return

    if command in {"menu", "home", "help"}:
        _send_main_menu(store, whatsapp, phone)
        return

    if text:
        whatsapp.send_text(phone, "Reply `menu` to see available options.")
