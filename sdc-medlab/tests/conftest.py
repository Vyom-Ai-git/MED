from __future__ import annotations

from dataclasses import dataclass

import mongomock
import pytest

from app import create_app


@dataclass
class FakeWhatsApp:
    calls: list

    def __init__(self):
        self.calls = []

    def send_text(self, phone, text):
        self.calls.append(("text", phone, text))
        return {"status": "ok"}

    def send_interactive_buttons(self, phone, body, buttons):
        self.calls.append(("interactive", phone, body, buttons))
        return {"status": "ok"}

    def send_document(self, phone, document_url, filename):
        self.calls.append(("document", phone, document_url, filename))
        return {"status": "ok"}

    def send_template(self, phone, template_name, language_code):
        self.calls.append(("template", phone, template_name, language_code))
        return {"status": "ok"}


class FakeGemini:
    def __init__(self, result=None, error=None):
        self.result = result or {
            "summary": "• Normal values are reassuring.\n• Attention values need follow-up.",
            "tests": [
                {
                    "name": "Hemoglobin",
                    "value": "11.2",
                    "unit": "g/dL",
                    "reference_range": "12-15",
                    "status": "low",
                    "explanation": "This is slightly below the reference range.",
                }
            ],
            "key_findings": ["Hemoglobin is slightly low"],
            "doctor_discussion": ["Ask whether iron studies are needed"],
            "safety_notice": "⚠️ This AI explanation is for informational purposes only and is not a diagnosis or medical advice. Please discuss your results with a qualified healthcare professional.",
        }
        self.error = error
        self.calls = []

    def analyze_report(self, report_text, language):
        self.calls.append((report_text, language))
        if self.error:
            raise self.error
        return self.result


class FakeLabOSClient:
    def __init__(self, *, report_metadata=None, patient=None, pdf_bytes=b"%PDF-1.4 fake pdf"):
        self.report_metadata = report_metadata
        self.patient = patient
        self.pdf_bytes = pdf_bytes
        self.calls = []

    def get_report_metadata(self, report_id):
        self.calls.append(("get_report_metadata", report_id))
        if isinstance(self.report_metadata, Exception):
            raise self.report_metadata
        return self.report_metadata or {}

    def download_report(self, report_id):
        self.calls.append(("download_report", report_id))

        class Response:
            def __init__(self, content):
                self.content = content

        return Response(self.pdf_bytes)

    def get_patient(self, patient_id):
        self.calls.append(("get_patient", patient_id))
        if isinstance(self.patient, Exception):
            raise self.patient
        return self.patient or {}


@pytest.fixture
def app_and_clients(monkeypatch, tmp_path):
    monkeypatch.setenv("META_VERIFY_TOKEN", "verify-token")
    monkeypatch.setenv("META_ACCESS_TOKEN", "meta-access")
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "phone-id")
    monkeypatch.setenv("META_API_VERSION", "v22.0")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("REPORT_INGEST_API_KEY", "ingest-key")
    monkeypatch.setenv("LABOS_WEBHOOK_SECRET", "labos-webhook-secret")
    monkeypatch.setenv("REPORT_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("MONGODB_DATABASE", "medlab_test")
    monkeypatch.setenv("TEST_MODE", "true")

    app = create_app(testing=True, mongo_client=mongomock.MongoClient())
    fake_whatsapp = FakeWhatsApp()
    fake_gemini = FakeGemini()
    app.config["WHATSAPP"] = fake_whatsapp
    app.config["GEMINI"] = fake_gemini
    return app, fake_whatsapp, fake_gemini


@pytest.fixture
def client(app_and_clients):
    app, _, _ = app_and_clients
    return app.test_client()


@pytest.fixture
def store(app_and_clients):
    app, _, _ = app_and_clients
    return app.config["STORE"]


@pytest.fixture
def fake_whatsapp(app_and_clients):
    return app_and_clients[1]


@pytest.fixture
def fake_gemini(app_and_clients):
    return app_and_clients[2]


@pytest.fixture
def fake_labos():
    return FakeLabOSClient()
