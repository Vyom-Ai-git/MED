"""
AI Report Assistant
--------------------
Turns a set of verified lab results into a plain-language explanation for
patients and front-desk staff, using Google Gemini.

Design notes:
- The model is instructed to explain, not diagnose or prescribe (see SYSTEM_PROMPT).
- A human (technician/pathologist) has already verified the underlying results
  before this ever runs — this only re-explains numbers that are already final.
- Every response carries a fixed safety disclaimer that the model cannot omit,
  enforced in code (not just via the prompt) by appending it server-side.
- Network/parsing failures degrade gracefully with a clear error, never a guess.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings

logger = logging.getLogger("app.services.ai_analysis")

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SAFETY_DISCLAIMER = (
    "This AI explanation is for informational purposes only and is not a "
    "diagnosis or medical advice. Please discuss these results with a "
    "qualified healthcare professional."
)

SYSTEM_PROMPT = """You are an AI assistant for Vyoma LabOS, helping explain laboratory test \
results in plain language to a patient or lab staff member.

Rules you must follow:
1. Explain what each value means in plain, reassuring, professional language.
2. Do NOT diagnose any disease or condition.
3. Do NOT prescribe or suggest medicines, supplements, or dosages.
4. Do NOT fabricate values that are not provided.
5. Clearly distinguish normal values from values that need attention.
6. Keep the overall summary under 120 words.
7. Suggest general discussion points for the patient's doctor, not conclusions.

Return ONLY strict JSON (no markdown, no commentary) with this exact shape:
{
  "summary": "short plain-language overview, under 120 words",
  "tests": [
    {
      "test_name": "string",
      "parameter_name": "string",
      "value": "string",
      "unit": "string",
      "reference_range": "string",
      "status": "normal | attention | critical | unknown",
      "explanation": "one or two plain-language sentences"
    }
  ],
  "key_findings": ["short bullet strings, normal vs attention grouped implicitly by status above"],
  "doctor_discussion": ["short bullet strings — topics worth raising with a doctor"]
}
"""


class AITestFinding(BaseModel):
    test_name: str = ""
    parameter_name: str = ""
    value: str = ""
    unit: str = ""
    reference_range: str = ""
    status: str = "unknown"
    explanation: str = ""


class AIReportAnalysis(BaseModel):
    summary: str
    tests: List[AITestFinding] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    doctor_discussion: List[str] = Field(default_factory=list)
    safety_notice: str = SAFETY_DISCLAIMER


class AIAnalysisError(RuntimeError):
    """Raised for any failure that should surface as a clean 4xx/5xx to the client."""


class GeminiReportAnalyzer:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL

    def _configured(self) -> bool:
        return bool(self.api_key and self.model)

    def _build_prompt(self, results: List[Dict[str, Any]], language: str) -> str:
        language_line = (
            "Write the response in English."
            if language != "ml"
            else "Write the response in Malayalam (മലയാളം)."
        )
        results_text = json.dumps(results, default=str, indent=2)
        return f"{SYSTEM_PROMPT}\n\n{language_line}\n\nLab results (structured JSON):\n{results_text}"

    def analyze(
        self, results: List[Dict[str, Any]], language: str = "en"
    ) -> Dict[str, Any]:
        if not self._configured():
            raise AIAnalysisError(
                "AI Report Assistant is not configured. Set GEMINI_API_KEY and GEMINI_MODEL."
            )
        if not results:
            raise AIAnalysisError("No verified results available to analyze for this report.")

        prompt = self._build_prompt(results, language)
        url = GEMINI_ENDPOINT.format(model=self.model)

        try:
            response = httpx.post(
                url,
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 1536,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=30.0,
            )
            response.raise_for_status()
            payload = response.json()
            candidates = payload.get("candidates") or []
            if not candidates:
                raise AIAnalysisError("AI service returned no analysis for this report.")

            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts).strip()
            if not text:
                raise AIAnalysisError("AI service returned an empty analysis.")

            parsed_json = json.loads(text)
            analysis = AIReportAnalysis.model_validate(parsed_json)
            # Server-side enforced disclaimer — never trust the model to include it verbatim.
            analysis.safety_notice = SAFETY_DISCLAIMER
            return analysis.model_dump()

        except httpx.HTTPStatusError as exc:
            logger.error("Gemini HTTP error: %s", exc.response.text[:500])
            raise AIAnalysisError("AI service request failed. Please try again shortly.") from exc
        except httpx.RequestError as exc:
            logger.error("Gemini request error: %s", exc)
            raise AIAnalysisError("Could not reach the AI service. Please try again shortly.") from exc
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Gemini returned malformed analysis: %s", exc)
            raise AIAnalysisError("AI service returned an unreadable analysis. Please try again.") from exc


ai_report_analyzer = GeminiReportAnalyzer()
