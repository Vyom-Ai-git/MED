from __future__ import annotations

EMERGENCY_KEYWORDS = {
    "chest pain",
    "trouble breathing",
    "shortness of breath",
    "severe bleeding",
    "unconscious",
    "fainting",
    "stroke",
    "heart attack",
    "seizure",
    "suicidal",
    "self-harm",
    "emergency",
}


def is_emergency_text(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in EMERGENCY_KEYWORDS)


def emergency_message() -> str:
    return (
        "Your message may describe an urgent health concern. "
        "Please seek immediate in-person medical care or contact local emergency services now. "
        "This chat will pause normal analysis until you restart it."
    )


def safe_ai_failure_message() -> str:
    return "Sorry, I couldn't safely analyze this report right now. Please try again later or contact our support team."
