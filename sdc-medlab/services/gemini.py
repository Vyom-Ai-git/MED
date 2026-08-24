from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError


logger = logging.getLogger(__name__)


class LabTestFinding(BaseModel):
    name: str = ""
    value: str = ""
    unit: str = ""
    reference_range: str = ""
    status: str = Field(default="unknown")
    explanation: str = ""


class LabAnalysis(BaseModel):
    summary: str
    tests: list[LabTestFinding] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    doctor_discussion: list[str] = Field(default_factory=list)
    safety_notice: str


class GeminiAnalysisError(RuntimeError):
    pass


def _prompt_path() -> Path:
    return Path(__file__).resolve().parents[1] / "prompts" / "medical_report_prompt.txt"


def _load_prompt() -> str:
    return _prompt_path().read_text(encoding="utf-8")


class GeminiAnalyzer:
    def __init__(self, config):
        self.config = config

    def _client(self):
        from google import genai

        return genai.Client(api_key=self.config.gemini_api_key)

    def _build_prompt(self, report_text: str, language: str) -> str:
        language_instruction = (
            "Write the response in English."
            if language == "en"
            else "Write the response in Malayalam (മലയാളം)."
        )
        return (
            f"{_load_prompt()}\n\n"
            f"{language_instruction}\n\n"
            "Return strict JSON with these keys: summary, tests, key_findings, doctor_discussion, safety_notice.\n"
            "Each item in tests must include: name, value, unit, reference_range, status, explanation.\n\n"
            f"Lab results:\n{report_text.strip()}"
        )

    def analyze_report(self, report_text: str, language: str) -> dict[str, Any]:
        if not self.config.gemini_api_key or not self.config.gemini_model:
            raise GeminiAnalysisError("Gemini is not configured")

        prompt = self._build_prompt(report_text, language)
        try:
            client = self._client()
            from google.genai import types

            response = client.models.generate_content(
                model=self.config.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=1024,
                ),
            )
            text = getattr(response, "text", "") or ""
            if not text:
                raise GeminiAnalysisError("Empty Gemini response")
            payload = json.loads(text)
            parsed = LabAnalysis.model_validate(payload)
            return parsed.model_dump()
        except ValidationError as exc:
            logger.exception("Malformed Gemini response")
            raise GeminiAnalysisError("Malformed Gemini response") from exc
        except Exception as exc:
            logger.exception("Gemini analysis failed")
            raise GeminiAnalysisError("Gemini analysis failed") from exc
