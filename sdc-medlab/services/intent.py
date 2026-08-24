from __future__ import annotations

from dataclasses import dataclass


GREETINGS = {
    "hi",
    "hii",
    "hello",
    "hey",
    "good morning",
    "good evening",
    "namaskaram",
}

MENU_COMMANDS = {"menu", "home", "start", "back", "help"}
CANCEL_COMMANDS = {"cancel", "restart", "stop"}
REPORT_COMMANDS = {"report", "report status", "view report", "show report", "ente report evide"}
LANGUAGE_COMMANDS = {"english", "en", "malayalam", "ml", "മലയാളം"}
DOCTOR_COMMANDS = {
    "doctor",
    "consult doctor",
    "doctor booking",
    "doctor booking venam",
    "consult a doctor",
}
LAB_COMMANDS = {
    "lab",
    "book lab",
    "book test",
    "lab test",
    "lab test book cheyyanam",
    "lab booking",
}
CARE_COMMANDS = {
    "customer care",
    "support",
    "help me",
    "i need help",
    "customer care venam",
}


@dataclass(slots=True)
class IntentResult:
    intent: str
    confidence: float = 1.0


def _normalize(text: str | None) -> str:
    return " ".join((text or "").strip().lower().split())


def detect_intent(text: str | None, *, button_id: str = "", button_title: str = "") -> IntentResult:
    candidate = _normalize(button_id or button_title or text)
    if candidate in CANCEL_COMMANDS:
        return IntentResult("cancel")
    if candidate in MENU_COMMANDS:
        return IntentResult("menu")
    if candidate in GREETINGS:
        return IntentResult("greeting")
    if candidate in LANGUAGE_COMMANDS or candidate in {"lang_en", "lang_ml"}:
        return IntentResult("language")
    if candidate in {"analyze_report", "analyze_sample_01"}:
        return IntentResult("report_analyze")
    if candidate in REPORT_COMMANDS:
        return IntentResult("report")
    if candidate in DOCTOR_COMMANDS:
        return IntentResult("doctor")
    if candidate in LAB_COMMANDS:
        return IntentResult("lab")
    if candidate in CARE_COMMANDS:
        return IntentResult("customer_care")
    if "report" in candidate and any(word in candidate for word in {"where", "explain", "summary", "details"}):
        return IntentResult("report")
    return IntentResult("unknown", confidence=0.2)
