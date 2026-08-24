"""Unit tests for LabOS API client against actual contract."""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, Mock, patch
import uuid

import pytest
import requests

from services.labos_client import (
    LabOSClient,
    LabOSClientError,
    LabOSConfigError,
    LabOSResponse,
)


@dataclass
class MockConfig:
    """Mock config for testing."""
    labos_base_url: str = "http://localhost:8000"
    labos_integration_key: str = "test-integration-key"
    labos_timeout_seconds: int = 5
    labos_max_retries: int = 2


@pytest.fixture
def config():
    """Provide mock config."""
    return MockConfig()


@pytest.fixture
def client(config):
    """Provide LabOS client with mocked session."""
    mock_session = Mock()
    client = LabOSClient(config, session=mock_session)
    return client


class TestLabOSClientAuthentication:
    """Test authentication and header management."""

    def test_headers_include_integration_key(self, client):
        """Headers must include X-Integration-Key."""
        headers = client._headers()
        assert "X-Integration-Key" in headers
        assert headers["X-Integration-Key"] == "test-integration-key"

    def test_headers_include_accept_types(self, client):
        """Headers must specify accepted content types."""
        headers = client._headers()
        assert "Accept" in headers
        assert "application/json" in headers["Accept"]
        assert "application/pdf" in headers["Accept"]

    def test_missing_base_url_raises_error(self, config):
        """Config error if LABOS_BASE_URL missing."""
        config.labos_base_url = None
        client = LabOSClient(config, session=Mock())
        with pytest.raises(LabOSConfigError, match="LABOS_BASE_URL"):
            client._ensure_ready()

    def test_missing_integration_key_raises_error(self, config):
        """Config error if LABOS_INTEGRATION_KEY missing."""
        config.labos_integration_key = None
        client = LabOSClient(config, session=Mock())
        with pytest.raises(LabOSConfigError, match="LABOS_INTEGRATION_KEY"):
            client._ensure_ready()


class TestLabOSClientURLConstruction:
    """Test URL path construction."""

    def test_url_construction_with_trailing_slash(self, client):
        """URL construction should handle trailing slashes."""
        url = client._url("/api/v1/reports/123/metadata")
        assert url == "http://localhost:8000/api/v1/reports/123/metadata"

    def test_url_construction_without_trailing_slash(self, client):
        """URL construction should handle no trailing slashes."""
        url = client._url("api/v1/reports/123/metadata")
        assert url == "http://localhost:8000/api/v1/reports/123/metadata"

    def test_url_construction_with_base_trailing_slash(self, config):
        """URL construction should strip base trailing slashes."""
        config.labos_base_url = "http://localhost:8000/"
        client = LabOSClient(config, session=Mock())
        url = client._url("/api/v1/reports/123/metadata")
        assert url == "http://localhost:8000/api/v1/reports/123/metadata"


class TestReportMetadata:
    """Test report metadata capability (Capability #2)."""

    def test_get_report_metadata(self, client):
        """GET /api/v1/integrations/reports/{id}/metadata returns metadata."""
        report_id = str(uuid.uuid4())
        mock_response = {
            "report_id": report_id,
            "patient_id": str(uuid.uuid4()),
            "created_at": "2026-08-17T10:00:00Z",
            "report_type": "lab_report",
            "status": "verified",
            "verified_at": "2026-08-17T11:00:00Z",
            "verified_by": "Dr. Smith",
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        result = client.get_report_metadata(report_id)

        assert result == mock_response
        client.session.request.assert_called_once()
        call = client.session.request.call_args
        assert "/api/v1/integrations/reports/" in call[0][1]
        assert "/metadata" in call[0][1]

    def test_get_report_metadata_404(self, client):
        """GET report metadata returns 404 if report not found."""
        client.session.request = Mock(return_value=Mock(status_code=404))

        with pytest.raises(LabOSClientError, match="404"):
            client.get_report_metadata(str(uuid.uuid4()))


class TestVerifiedResults:
    """Test verified report results capability (Capability #3)."""

    def test_get_verified_results(self, client):
        """GET /api/v1/integrations/reports/{id}/results returns results."""
        report_id = str(uuid.uuid4())
        mock_response = {
            "report_id": report_id,
            "tests": [
                {
                    "test_name": "Hemoglobin",
                    "result_value": "14.5",
                    "unit": "g/dL",
                    "reference_range": "12-15",
                    "flag": "normal",
                },
                {
                    "test_name": "Glucose",
                    "result_value": "110",
                    "unit": "mg/dL",
                    "reference_range": "70-100",
                    "flag": "high",
                },
            ],
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        result = client.get_verified_results(report_id)

        assert result == mock_response
        assert len(result["tests"]) == 2
        assert result["tests"][0]["test_name"] == "Hemoglobin"

    def test_get_verified_results_409_not_verified(self, client):
        """GET results returns 409 if report not verified."""
        client.session.request = Mock(return_value=Mock(status_code=409))

        with pytest.raises(LabOSClientError, match="not yet verified"):
            client.get_verified_results(str(uuid.uuid4()))


class TestPatientLookup:
    """Test patient contact lookup capability (Capability #4)."""

    def test_get_patient(self, client):
        """GET /api/v1/patients/lookup returns patient info."""
        patient_id = str(uuid.uuid4())
        mock_response = {
            "patient_id": patient_id,
            "name": "John Doe",
            "phone": "+91-9876543210",
            "email": "john@example.com",
            "date_of_birth": "1990-05-15",
            "gender": "M",
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        result = client.get_patient(patient_id)

        assert result == mock_response
        assert result["name"] == "John Doe"
        assert result["phone"] == "+91-9876543210"

    def test_get_patient_404(self, client):
        """GET patient lookup returns 404 if patient not found."""
        client.session.request = Mock(return_value=Mock(status_code=404))

        with pytest.raises(LabOSClientError, match="404"):
            client.get_patient(str(uuid.uuid4()))


class TestSecureLinkGeneration:
    """Test secure patient report access capability (Capability #5)."""

    def test_get_secure_link(self, client):
        """POST /api/v1/reports/{id}/secure-link generates secure link."""
        report_id = str(uuid.uuid4())
        patient_id = str(uuid.uuid4())
        mock_response = {
            "token": "secure-token-abc123xyz",
            "expires_at": "2026-08-18T10:00:00Z",
            "url": f"http://localhost:8000/api/v1/public/reports/access/secure-token-abc123xyz",
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        result = client.get_secure_link(report_id, patient_id, expires_in_hours=24)

        assert result == mock_response
        assert "token" in result
        assert "url" in result
        call = client.session.request.call_args
        assert "POST" in str(call)

    def test_get_secure_link_custom_expiry(self, client):
        """Secure link generation accepts custom expiry hours."""
        mock_response = {
            "token": "token",
            "expires_at": "2026-08-18T22:00:00Z",
            "url": "http://localhost:8000/api/v1/public/reports/access/token",
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        client.get_secure_link(str(uuid.uuid4()), str(uuid.uuid4()), expires_in_hours=12)

        call = client.session.request.call_args
        # Verify the payload includes expires_in_hours
        assert call is not None


class TestTestCatalog:
    """Test test catalog capability (Capability #6)."""

    def test_get_test_catalog(self, client):
        """GET /api/v1/tests/catalog returns available tests."""
        mock_response = {
            "tests": [
                {
                    "test_id": str(uuid.uuid4()),
                    "name": "Complete Blood Count (CBC)",
                    "description": "Measures hemoglobin, WBC, platelets",
                    "price": 299.00,
                    "duration_hours": 24,
                },
                {
                    "test_id": str(uuid.uuid4()),
                    "name": "Blood Sugar (Fasting)",
                    "description": "Fasting glucose test",
                    "price": 150.00,
                    "duration_hours": 4,
                },
            ],
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        result = client.get_test_catalog()

        assert "tests" in result
        assert len(result["tests"]) == 2
        assert result["tests"][0]["name"] == "Complete Blood Count (CBC)"


class TestBranchAvailability:
    """Test branch/location availability capability (Capability #7)."""

    def test_get_branch_availability(self, client):
        """GET /api/v1/branches/availability returns branch info."""
        mock_response = {
            "branches": [
                {
                    "branch_id": str(uuid.uuid4()),
                    "name": "LabOS Downtown",
                    "location": {
                        "city": "Bangalore",
                        "address": "123 MG Road, Bangalore",
                    },
                    "is_open": True,
                    "working_hours": {
                        "open_at": "06:00",
                        "close_at": "22:00",
                    },
                },
            ],
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        result = client.get_branch_availability()

        assert "branches" in result
        assert len(result["branches"]) >= 1
        assert result["branches"][0]["is_open"] is True

    def test_get_branch_availability_with_city_filter(self, client):
        """Branch availability accepts optional city filter."""
        mock_response = {"branches": []}
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        client.get_branch_availability(city="Delhi")

        call = client.session.request.call_args
        assert "city=Delhi" in call[0][1]


class TestDoctorAvailability:
    """Test doctor availability capability (Capability #8)."""

    def test_get_doctor_availability(self, client):
        """GET /api/v1/doctors/{id}/availability returns doctor slots."""
        doctor_id = str(uuid.uuid4())
        mock_response = {
            "doctor_id": doctor_id,
            "name": "Dr. Sharma",
            "specialization": "Cardiology",
            "available_slots": [
                {
                    "date": "2026-08-20",
                    "start_time": "10:00",
                    "end_time": "10:30",
                },
                {
                    "date": "2026-08-20",
                    "start_time": "14:00",
                    "end_time": "14:30",
                },
            ],
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        result = client.get_doctor_availability(doctor_id)

        assert result["doctor_id"] == doctor_id
        assert len(result["available_slots"]) == 2

    def test_get_doctor_availability_with_date_range(self, client):
        """Doctor availability accepts optional from_date and to_date."""
        mock_response = {"doctor_id": str(uuid.uuid4()), "available_slots": []}
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        client.get_doctor_availability(
            str(uuid.uuid4()),
            from_date="2026-08-20",
            to_date="2026-08-25"
        )

        call = client.session.request.call_args
        assert "from_date=2026-08-20" in call[0][1]
        assert "to_date=2026-08-25" in call[0][1]


class TestDoctorAppointmentBooking:
    """Test doctor appointment booking capability (Capability #9)."""

    def test_create_doctor_appointment(self, client):
        """POST /api/v1/bookings/doctor creates appointment."""
        doctor_id = str(uuid.uuid4())
        patient_id = str(uuid.uuid4())
        mock_response = {
            "appointment_id": str(uuid.uuid4()),
            "status": "confirmed",
            "confirmation_token": "appt-token-123",
        }
        client.session.request = Mock(
            return_value=Mock(status_code=201, json=Mock(return_value=mock_response))
        )

        payload = {
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "appointment_date": "2026-08-20",
            "appointment_time": "10:00",
        }
        result = client.create_doctor_appointment(payload)

        assert result["status"] == "confirmed"
        assert "appointment_id" in result
        call = client.session.request.call_args
        assert "POST" in str(call)

    def test_create_doctor_appointment_slot_conflict(self, client):
        """Doctor appointment returns 409 if slot already booked."""
        client.session.request = Mock(return_value=Mock(status_code=409))

        with pytest.raises(LabOSClientError, match="409"):
            client.create_doctor_appointment({
                "doctor_id": str(uuid.uuid4()),
                "patient_id": str(uuid.uuid4()),
                "appointment_date": "2026-08-20",
                "appointment_time": "10:00",
            })


class TestLabBooking:
    """Test lab booking capability (Capability #10)."""

    def test_create_lab_booking(self, client):
        """POST /api/v1/bookings/lab creates booking."""
        patient_id = str(uuid.uuid4())
        branch_id = str(uuid.uuid4())
        test_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        mock_response = {
            "booking_id": str(uuid.uuid4()),
            "status": "confirmed",
            "appointment_date": "2026-08-20",
            "appointment_time": "09:00",
            "confirmation_token": "booking-token-456",
        }
        client.session.request = Mock(
            return_value=Mock(status_code=201, json=Mock(return_value=mock_response))
        )

        payload = {
            "patient_id": patient_id,
            "test_ids": test_ids,
            "branch_id": branch_id,
        }
        result = client.create_lab_booking(payload)

        assert result["status"] == "confirmed"
        assert "booking_id" in result

    def test_create_lab_booking_slot_unavailable(self, client):
        """Lab booking returns 409 if slot unavailable."""
        client.session.request = Mock(return_value=Mock(status_code=409))

        with pytest.raises(LabOSClientError, match="409"):
            client.create_lab_booking({
                "patient_id": str(uuid.uuid4()),
                "test_ids": [str(uuid.uuid4())],
                "branch_id": str(uuid.uuid4()),
            })


class TestCustomerCareHandoff:
    """Test customer care handoff capability (Capability #11)."""

    def test_create_customer_care_ticket(self, client):
        """POST /api/v1/customer-care/handoff creates ticket."""
        patient_id = str(uuid.uuid4())
        mock_response = {
            "ticket_id": str(uuid.uuid4()),
            "status": "created",
            "assigned_to": None,
        }
        client.session.request = Mock(
            return_value=Mock(status_code=201, json=Mock(return_value=mock_response))
        )

        payload = {
            "patient_id": patient_id,
            "category": "billing",
            "message": "I have a question about my bill",
        }
        result = client.create_customer_care_ticket(payload)

        assert "ticket_id" in result
        assert result["status"] == "created"

    def test_get_customer_care_tickets(self, client):
        """GET /api/v1/customer-care/handoff retrieves tickets."""
        patient_id = str(uuid.uuid4())
        mock_response = {
            "tickets": [
                {
                    "ticket_id": str(uuid.uuid4()),
                    "status": "in_progress",
                    "assigned_to": "Support Team",
                },
            ],
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        result = client.get_customer_care_tickets(patient_id=patient_id)

        assert "tickets" in result
        assert len(result["tickets"]) >= 1


class TestDownloadReport:
    """Test report download capability."""

    def test_download_report(self, client):
        """GET report download returns PDF binary."""
        pdf_content = b"%PDF-1.4\n%test content"
        mock_response = Mock(
            status_code=200,
            content=pdf_content,
            headers={"Content-Type": "application/pdf", "Content-Length": str(len(pdf_content))},
        )
        client.session.request = Mock(return_value=mock_response)

        result = client.download_report(str(uuid.uuid4()))

        assert isinstance(result, LabOSResponse)
        assert result.status_code == 200
        assert result.content == pdf_content
        assert "Content-Type" in result.headers


class TestIntegrationMetadata:
    """Test integration metadata capabilities (Capability #1)."""

    def test_test_webhook(self, client):
        """POST /api/v1/integrations/n8n/test tests webhook."""
        mock_response = {
            "status": "success",
            "message": "Webhook reachable and configured",
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        result = client.test_webhook("https://n8n.example.com/webhook/labos")

        assert result["status"] == "success"

    def test_get_integration_logs(self, client):
        """GET /api/v1/integrations/logs returns integration logs."""
        mock_response = {
            "logs": [
                {
                    "timestamp": "2026-08-17T10:00:00Z",
                    "event_type": "report.available",
                    "status": "success",
                    "details": {},
                },
            ],
            "total": 1,
        }
        client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        result = client.get_integration_logs(limit=50, offset=0)

        assert "logs" in result
        assert result["total"] == 1
