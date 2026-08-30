from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader
from werkzeug.utils import secure_filename

from services.safety import emergency_message, is_emergency_text, safe_ai_failure_message


logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    extracted = []
    for page in reader.pages:
        extracted.append(page.extract_text() or "")
    return "\n".join(extracted).strip()


def ensure_storage_dir(path: str) -> Path:
    storage = Path(path)
    storage.mkdir(parents=True, exist_ok=True)
    return storage


def normalize_language(language: str | None) -> str:
    if not language:
        return "en"
    lowered = language.lower()
    if lowered in {"ml", "malayalam", "മലയാളം"}:
        return "ml"
    return "en"


def build_analysis_buttons() -> list[dict[str, str]]:
    return [
        {"id": "book_test", "title": "Book Test"},
        {"id": "consult_doctor", "title": "Consult Doctor"},
        {"id": "customer_support", "title": "Customer Support"},
    ]


def build_language_buttons() -> list[dict[str, str]]:
    return [
        {"id": "lang_en", "title": "English"},
        {"id": "lang_ml", "title": "മലയാളം"},
    ]


def build_report_buttons() -> list[dict[str, str]]:
    return [
        {"id": "view_report", "title": "View Report"},
        {"id": "analyze_report", "title": "Analyze with AI"},
        {"id": "book_test", "title": "Book Test"},
    ]


def build_labos_report_buttons() -> list[dict[str, str]]:
    return [
        {"id": "view_report", "title": "View Report"},
        {"id": "analyze_report", "title": "Analyze with AI"},
    ]


def safe_report_message() -> str:
    return "No report is linked to this conversation yet. Please ask your lab to send a report first."


def critical_escalation_message(language: str = "en") -> str:
    if normalize_language(language) == "ml":
        return (
            "നിങ്ങളുടെ ലബോറട്ടറി റിപ്പോർട്ടിൽ ലബോറട്ടറി നിർണായകമായി അടയാളപ്പെടുത്തിയ ഒരു ഫലം ഉൾപ്പെട്ടിരിക്കുന്നു. "
            "ദയവായി ഉടൻ തന്നെ നിങ്ങളുടെ ആരോഗ്യപരിചരണ ദാതാവുമായി ബന്ധപ്പെടുക. "
            "പൂർണ്ണ വിവരങ്ങൾക്ക് നിങ്ങളുടെ ഔദ്യോഗിക റിപ്പോർട്ട് കാണുക."
        )
    return (
        "Your laboratory report contains a result marked as critical by the laboratory. "
        "Please contact your healthcare provider promptly for appropriate medical guidance. "
        "Please refer to your official report for the complete details."
    )


def fallback_summary_message(language: str = "en") -> str:
    if normalize_language(language) == "ml":
        return (
            "നിങ്ങളുടെ ലബോറട്ടറി റിപ്പോർട്ട് ലഭ്യമാണ്. പൂർണ്ണ വിവരങ്ങൾക്ക് ഔദ്യോഗിക റിപ്പോർട്ട് കാണുക. "
            "വ്യാഖ്യാനത്തിനോ മെഡിക്കൽ ഉപദേശത്തിനോ യോഗ്യതയുള്ള ആരോഗ്യപരിചരണ വിദഗ്ധനെ സമീപിക്കുക."
        )
    return (
        "Your laboratory report is available. Please refer to the official report for complete details. "
        "For interpretation or medical advice, please consult a qualified healthcare professional."
    )


def report_ready_message(patient_name: str | None, report_number: str | None) -> str:
    name = patient_name or "there"
    number = report_number or "your report"
    return (
        f"Hello {name},\n\n"
        f"Your laboratory report {number} is now available.\n"
        "Use the buttons below to view the report or generate a summary."
    )


class ReportService:
    def __init__(self, store, whatsapp, gemini, config):
        self.store = store
        self.whatsapp = whatsapp
        self.gemini = gemini
        self.config = config

    def _report_path(self, report_uuid: str, filename: str) -> Path:
        storage = ensure_storage_dir(self.config.report_storage_dir)
        return storage / f"{report_uuid}-{secure_filename(filename)}"

    def ingest_report(
        self,
        *,
        phone: str,
        patient_id: str,
        report_id: str,
        report_type: str,
        report_date: str,
        file_bytes: bytes,
        filename: str,
        pdf_url: str | None = None,
        report_uuid: str | None = None,
    ) -> dict[str, Any]:
        if not phone or not report_id:
            raise ValueError("phone and report_id are required")
        if len(file_bytes) > self.config.max_content_length:
            raise ValueError("PDF exceeds configured maximum size")

        if self.store.report_exists(report_id, report_uuid):
            raise FileExistsError("Duplicate report")

        report_uuid = report_uuid or str(uuid4())
        path = self._report_path(report_uuid, filename)
        path.write_bytes(file_bytes)

        report_doc = {
            "report_id": report_id,
            "report_uuid": report_uuid,
            "phone": phone,
            "patient_id": patient_id,
            "report_type": report_type,
            "report_date": report_date,
            "pdf_url": pdf_url or str(path),
            "storage_key": str(path),
            "pdf_sha256": sha256_bytes(file_bytes),
            "extracted_text": "",
            "summary_en": None,
            "summary_ml": None,
            "summary_model": None,
            "processing_ms": 0,
            "summarized_at": None,
            "created_at": utcnow(),
            "status": "received",
        }
        self.store.upsert_report(report_doc)
        self.store.log_event("REPORT_RECEIVED", phone=phone, report_id=report_id, component="reports", status="received")
        return report_doc

    def cache_labos_report(
        self,
        *,
        phone: str,
        patient_id: str,
        report_id: str,
        report_number: str,
        file_bytes: bytes,
        filename: str,
        organization_id: str | None = None,
        branch_id: str | None = None,
        order_id: str | None = None,
        structured_result: dict[str, Any] | None = None,
        critical_flag: bool = False,
        patient_name: str | None = None,
        source_event_id: str | None = None,
    ) -> dict[str, Any]:
        report_uuid = structured_result.get("report_uuid") if structured_result else None
        report_uuid = report_uuid or str(uuid4())
        path = self._report_path(report_uuid, filename)
        path.write_bytes(file_bytes)
        report_doc = {
            "report_id": report_id,
            "report_uuid": report_uuid,
            "report_number": report_number,
            "phone": phone,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "organization_id": organization_id,
            "branch_id": branch_id,
            "order_id": order_id,
            "report_type": "lab_report",
            "report_date": utcnow().date().isoformat(),
            "pdf_url": None,
            "storage_key": str(path),
            "pdf_sha256": sha256_bytes(file_bytes),
            "extracted_text": "",
            "structured_result": structured_result or {},
            "critical_flag": critical_flag,
            "summary_en": None,
            "summary_ml": None,
            "summary_model": None,
            "processing_ms": 0,
            "summarized_at": None,
            "created_at": utcnow(),
            "status": "received",
            "source_system": "labos",
            "source_event_id": source_event_id,
        }
        self.store.upsert_report(report_doc)
        self.store.log_event(
            "REPORT_RECEIVED",
            phone=phone,
            report_id=report_id,
            component="labos",
            status="received",
        )
        return report_doc

    def build_verified_summary(self, report: dict[str, Any], language: str) -> dict[str, Any]:
        language = normalize_language(language)
        structured = report.get("structured_result") or {}
        if report.get("critical_flag") or structured.get("critical_flag"):
            summary = critical_escalation_message(language)
            return {
                "summary": summary,
                "tests": [],
                "key_findings": [],
                "doctor_discussion": [],
                "safety_notice": summary,
                "language": language,
            }

        tests = structured.get("tests") or structured.get("result_items") or []
        if tests:
            normal = 0
            attention = 0
            for item in tests:
                flag = str(item.get("flag") or item.get("status") or "unknown").lower()
                if flag in {"normal", "ok", "within_range"}:
                    normal += 1
                elif flag in {"high", "low", "critical", "abnormal", "elevated"}:
                    attention += 1
            total = len(tests)
            if language == "ml":
                summary = (
                    "നിങ്ങളുടെ ലബോറട്ടറി റിപ്പോർട്ട് ലഭ്യമാണ്.\n\n"
                    f"• മൊത്തം പരിശോധനകൾ: {total}\n"
                    f"• സാധാരണ പരിധിയിലുള്ളവ: {normal}\n"
                    f"• ശ്രദ്ധ ആവശ്യമായവ: {attention}\n\n"
                    "പൂർണ്ണ റിപ്പോർട്ടിൽ നൽകിയിരിക്കുന്ന വിവരങ്ങൾക്കായി ദയവായി നിങ്ങളുടെ ഡോക്ടറുമായി ചർച്ച ചെയ്യുക."
                )
            else:
                summary = (
                    "Your laboratory report is now available.\n\n"
                    f"• Total tests: {total}\n"
                    f"• Within range: {normal}\n"
                    f"• Attention needed: {attention}\n\n"
                    "Please review the official report with your doctor for proper clinical interpretation."
                )
            key_findings = []
            if attention:
                key_findings.append("Some values are outside the reference range shown in the report.")
            else:
                key_findings.append("The report values provided are mostly within the reference ranges shown.")
            return {
                "summary": summary,
                "tests": tests,
                "key_findings": key_findings,
                "doctor_discussion": [
                    "Discuss any abnormal or critical values with a qualified healthcare professional."
                ],
                "safety_notice": fallback_summary_message(language),
                "language": language,
            }

        return {
            "summary": fallback_summary_message(language),
            "tests": [],
            "key_findings": [],
            "doctor_discussion": [],
            "safety_notice": fallback_summary_message(language),
            "language": language,
        }

    def render_summary_text(self, summary_payload: dict[str, Any]) -> str:
        return summary_payload.get("summary", fallback_summary_message(summary_payload.get("language", "en")))

    def _read_report_text(self, report: dict[str, Any]) -> str:
        extracted = (report.get("extracted_text") or "").strip()
        if extracted:
            return extracted
        storage_key = report.get("storage_key")
        if not storage_key or not Path(storage_key).exists():
            return ""
        text = extract_pdf_text(storage_key)
        if text:
            self.store.update_report(report["report_id"], {"extracted_text": text})
        return text

    def _report_for_phone(self, phone: str, active_report_id: str | None = None) -> dict[str, Any] | None:
        if active_report_id:
            report = self.store.get_report_by_phone_and_id(phone, active_report_id)
            if report:
                return report
        return self.store.get_latest_report_by_phone(phone)

    def _labos_report_text(self, report: dict[str, Any]) -> str:
        """Build a stable Gemini input from verified LabOS fields."""
        structured = report.get("structured_result") or {}
        tests = structured.get("tests") or structured.get("result_items") or []
        lines = [
            f"Patient: {report.get('patient_name') or 'Not provided'}",
            f"Report number: {report.get('report_number') or report.get('report_id')}",
            "Verified laboratory results:",
        ]
        for item in tests:
            if not isinstance(item, dict):
                continue
            name = item.get("test_name") or item.get("name") or item.get("parameter") or "Test"
            value = item.get("result_value")
            if value is None:
                value = item.get("value") or item.get("result") or "Not provided"
            unit = item.get("unit") or item.get("units") or ""
            reference = item.get("reference_range") or item.get("reference") or item.get("normal_range") or "Not provided"
            flag = item.get("flag") or item.get("status") or item.get("interpretation") or "Not provided"
            lines.append(
                f"- {name}: {value} {unit}; reference range: {reference}; flag: {flag}"
            )
        return "\n".join(lines)

    def analyze_report_for_phone(self, phone: str, language: str) -> dict[str, Any]:
        language = normalize_language(language)
        state = self.store.get_state(phone)
        report = self._report_for_phone(phone, state.get("active_report_id"))
        if not report:
            raise LookupError("No report linked to phone")
        if report.get("critical_flag"):
            summary = critical_escalation_message(language)
            self.store.update_report(report["report_id"], {f"summary_{language}": summary, "status": "processed"})
            return {"cached": True, "analysis": {"summary": summary, "tests": [], "key_findings": [], "doctor_discussion": [], "safety_notice": summary}, "report": report}
        if report.get("source_system") == "labos":
            cached_summary = report.get("summary_en") if language == "en" else report.get("summary_ml")
            if cached_summary:
                return {
                    "cached": True,
                    "analysis": {
                        "summary": cached_summary,
                        "tests": [],
                        "key_findings": [],
                        "doctor_discussion": [],
                        "safety_notice": "This AI explanation is for informational purposes only and is not a diagnosis or medical advice.",
                    },
                    "report": report,
                }
            report_text = self._labos_report_text(report)
            if len(report_text.strip()) < 20:
                self.store.log_event(
                    "REQUIRES_LABOS_VERIFIED_RESULT_API",
                    phone=phone,
                    report_id=report["report_id"],
                    component="reports",
                    status=language,
                )
                report_text = self._read_report_text(report)
            if report_text and is_emergency_text(report_text):
                self.store.set_state(phone, "emergency_halt", language=language, active_report_id=report["report_id"])
                raise RuntimeError(emergency_message())
            if len(report_text.strip()) < 20:
                self.store.update_report(report["report_id"], {"status": "failed"})
                raise ValueError("Verified LabOS report data is missing or insufficient for safe analysis")
            start = utcnow()
            self.store.log_event("ANALYSIS_STARTED", phone=phone, report_id=report["report_id"], component="gemini", status=language)
            analysis = self.gemini.analyze_report(report_text, language)
            summary_text = analysis.get("summary", "").strip()
            if not summary_text:
                raise ValueError("Gemini response is missing summary")
            elapsed = int((utcnow() - start).total_seconds() * 1000)
            updates = {
                f"summary_{language}": summary_text,
                "summary_model": self.config.gemini_model,
                "processing_ms": elapsed,
                "summarized_at": utcnow(),
                "status": "processed",
            }
            self.store.update_report(report["report_id"], updates)
            self.store.log_event("ANALYSIS_COMPLETED", phone=phone, report_id=report["report_id"], component="gemini", status=language, processing_ms=elapsed)
            return {"cached": False, "analysis": analysis, "report": report}
        report_text = self._read_report_text(report)
        if report_text and is_emergency_text(report_text):
            self.store.set_state(phone, "emergency_halt", language=language, active_report_id=report["report_id"])
            raise RuntimeError(emergency_message())

        cached_summary = report.get("summary_en") if language == "en" else report.get("summary_ml")
        if cached_summary:
            self.store.log_event("ANALYSIS_CACHED", phone=phone, report_id=report["report_id"], component="reports", status=language)
            return {"cached": True, "analysis": report, "report": report}

        if len(report_text.strip()) < 20:
            self.store.update_report(report["report_id"], {"status": "failed"})
            raise ValueError("Report text is missing or insufficient for safe analysis")

        start = utcnow()
        self.store.log_event("ANALYSIS_STARTED", phone=phone, report_id=report["report_id"], component="gemini", status=language)
        analysis = self.gemini.analyze_report(report_text, language)
        elapsed = int((utcnow() - start).total_seconds() * 1000)
        summary_text = analysis.get("summary", "").strip()
        if not summary_text:
            raise ValueError("Gemini response is missing summary")

        updates: dict[str, Any] = {
            "summary_model": self.config.gemini_model,
            "processing_ms": elapsed,
            "summarized_at": utcnow(),
            "status": "processed",
            "extracted_text": report_text,
        }
        if language == "en":
            updates["summary_en"] = summary_text
        else:
            updates["summary_ml"] = summary_text
        self.store.update_report(report["report_id"], updates)
        self.store.log_event("ANALYSIS_COMPLETED", phone=phone, report_id=report["report_id"], component="gemini", status=language, processing_ms=elapsed)
        return {"cached": False, "analysis": analysis, "report": report}

    def summarize_verified_report(self, report: dict[str, Any], language: str) -> dict[str, Any]:
        summary_payload = self.build_verified_summary(report, language)
        language = normalize_language(language)
        updates: dict[str, Any] = {
            "summary_model": self.config.gemini_model or "deterministic",
            "status": "processed",
            "summarized_at": utcnow(),
        }
        if language == "en":
            updates["summary_en"] = summary_payload["summary"]
        else:
            updates["summary_ml"] = summary_payload["summary"]
        self.store.update_report(report["report_id"], updates)
        return summary_payload

    def format_analysis_message(self, analysis: dict[str, Any], language: str) -> str:
        tests = analysis.get("tests", []) or []
        key_findings = analysis.get("key_findings", []) or []
        doctor_discussion = analysis.get("doctor_discussion", []) or []
        safety_notice = analysis.get("safety_notice") or "Disclaimer: This AI summary is for informational purposes only. Please consult your physician for clinical advice."

        def _format_line(label: str, value: str) -> str:
            return f"{label.ljust(16)}: {value}".rstrip()

        lines = ["AI Report Summary (SDC Labs)", ""]
        summary = analysis.get("summary", "").strip()
        if summary:
            lines.append(summary)
            lines.append("")
        if tests:
            lines.append("Results:")
            for item in tests[:8]:
                name = str(item.get("name", "Test")).strip()
                value = str(item.get("value", "")).strip()
                unit = str(item.get("unit", "")).strip()
                status = str(item.get("status", "")).strip()
                explanation = str(item.get("explanation", "")).strip()
                combined_value = " ".join(part for part in [value, unit] if part).strip()
                if status and status.lower() not in {"normal", "within normal range"}:
                    combined_value = f"{combined_value} ({status})" if combined_value else f"({status})"
                lines.append(_format_line(name, combined_value or "not available"))
                if explanation:
                    lines.append(f"  Note: {explanation}")
            lines.append("")
        if key_findings:
            lines.append("Key findings:")
            lines.extend([f"- {entry}" for entry in key_findings[:6]])
            lines.append("")
        if doctor_discussion:
            lines.append("Discuss with your doctor:")
            lines.extend([f"- {entry}" for entry in doctor_discussion[:6]])
            lines.append("")
        lines.append(safety_notice)
        return "\n".join(lines).strip()

    def send_analysis_result(self, phone: str, analysis_payload: dict[str, Any], language: str) -> None:
        message = self.format_analysis_message(analysis_payload, language)
        self.whatsapp.send_text(phone, message)
        self.whatsapp.send_interactive_buttons(phone, "What would you like to do next?", build_analysis_buttons())

    def send_report_ready(
        self,
        phone: str,
        document_url: str | None = None,
        filename: str | None = None,
    ) -> None:
        if document_url:
            self.whatsapp.send_document(phone, document_url, filename or "lab-report.pdf")
        self.whatsapp.send_interactive_buttons(
            phone,
            "Your lab report is ready.",
            build_report_buttons(),
        )

    def send_labos_report_ready(
        self,
        phone: str,
        patient_name: str | None,
        report_number: str | None,
        document_url: str | None = None,
        filename: str | None = None,
    ) -> None:
        if document_url:
            self.whatsapp.send_document(phone, document_url, filename or "lab-report.pdf")
        self.whatsapp.send_interactive_buttons(
            phone,
            report_ready_message(patient_name, report_number),
            build_labos_report_buttons(),
        )
