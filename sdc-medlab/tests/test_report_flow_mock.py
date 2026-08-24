"""End-to-end report delivery flow tests with mocked LabOS API."""
from __future__ import annotations

from unittest.mock import Mock, patch
import uuid

import pytest

from services.labos_client import LabOSClient, LabOSClientError
from services.report_access import ReportAccessService
from services.booking_adapters import (
    DoctorBookingService,
    LabBookingService,
    CustomerCareService,
)


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = Mock()
    config.labos_base_url = "http://localhost:8000"
    config.labos_integration_key = "test-key"
    config.labos_timeout_seconds = 5
    config.labos_max_retries = 2
    return config


@pytest.fixture
def mock_session():
    """Mock requests session."""
    return Mock()


@pytest.fixture
def labos_client(mock_config, mock_session):
    """LabOS client with mocked session."""
    return LabOSClient(mock_config, session=mock_session)


class TestReportAccessFlow:
    """Test report access and secure link generation."""

    def test_get_patient_facing_url_generates_secure_link(self, labos_client):
        """ReportAccessService generates secure link using LabOS API."""
        report_id = str(uuid.uuid4())
        patient_id = str(uuid.uuid4())

        mock_response = {
            "token": "secure-token-xyz",
            "expires_at": "2026-08-18T10:00:00Z",
            "url": f"http://localhost:8000/api/v1/public/reports/access/secure-token-xyz",
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=mock_response))
        )

        service = ReportAccessService(Mock(), labos_client=labos_client)
        report = {"report_id": report_id, "patient_id": patient_id}

        url = service.get_patient_facing_url(report, expires_in_hours=24)

        assert url == mock_response["url"]
        assert "secure-token-xyz" in url

    def test_get_patient_facing_url_handles_labos_error(self, labos_client):
        """ReportAccessService handles LabOS API errors gracefully."""
        labos_client.session.request = Mock(return_value=Mock(status_code=404))

        service = ReportAccessService(Mock(), labos_client=labos_client)
        report = {"report_id": str(uuid.uuid4()), "patient_id": str(uuid.uuid4())}

        with pytest.raises(LabOSClientError):
            service.get_patient_facing_url(report)


class TestDoctorBookingFlow:
    """Test doctor appointment booking flow."""

    def test_doctor_booking_workflow(self, labos_client):
        """Complete doctor booking workflow."""
        doctor_id = str(uuid.uuid4())
        patient_id = str(uuid.uuid4())

        # Step 1: Get available dates
        availability_response = {
            "doctor_id": doctor_id,
            "name": "Dr. Sharma",
            "specialization": "Cardiology",
            "available_slots": [
                {"date": "2026-08-20", "start_time": "10:00", "end_time": "10:30"},
                {"date": "2026-08-20", "start_time": "14:00", "end_time": "14:30"},
                {"date": "2026-08-21", "start_time": "09:00", "end_time": "09:30"},
            ],
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=availability_response))
        )

        service = DoctorBookingService(labos_client)
        dates = service.get_available_dates(doctor_id)

        assert "2026-08-20" in dates
        assert "2026-08-21" in dates

        # Step 2: Get slots for a date
        slots = service.get_available_slots(doctor_id, "2026-08-20")
        assert len(slots) == 2
        assert slots[0]["date"] == "2026-08-20"

        # Step 3: Create booking
        booking_response = {
            "appointment_id": str(uuid.uuid4()),
            "status": "confirmed",
            "confirmation_token": "appt-token-123",
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=201, json=Mock(return_value=booking_response))
        )

        booking = service.create_booking(doctor_id, patient_id, "2026-08-20", "10:00")

        assert booking["status"] == "confirmed"
        assert "appointment_id" in booking


class TestLabBookingFlow:
    """Test lab test booking flow."""

    def test_lab_booking_workflow(self, labos_client):
        """Complete lab booking workflow."""
        patient_id = str(uuid.uuid4())
        branch_id = str(uuid.uuid4())

        # Step 1: Get available tests
        catalog_response = {
            "tests": [
                {
                    "test_id": str(uuid.uuid4()),
                    "name": "Complete Blood Count",
                    "price": 299.00,
                    "duration_hours": 24,
                },
                {
                    "test_id": str(uuid.uuid4()),
                    "name": "Blood Sugar",
                    "price": 150.00,
                    "duration_hours": 4,
                },
            ],
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=catalog_response))
        )

        service = LabBookingService(labos_client)
        tests = service.get_tests()

        assert len(tests["tests"]) == 2
        assert tests["tests"][0]["name"] == "Complete Blood Count"

        # Step 2: Get available branches
        branches_response = {
            "branches": [
                {
                    "branch_id": str(uuid.uuid4()),
                    "name": "LabOS Downtown",
                    "location": {"city": "Bangalore", "address": "123 MG Road"},
                    "is_open": True,
                    "working_hours": {"open_at": "06:00", "close_at": "22:00"},
                },
            ],
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=branches_response))
        )

        branches = service.get_branches()
        assert len(branches["branches"]) == 1
        assert branches["branches"][0]["is_open"] is True

        # Step 3: Create booking
        test_ids = [t["test_id"] for t in tests["tests"]]
        booking_response = {
            "booking_id": str(uuid.uuid4()),
            "status": "confirmed",
            "appointment_date": "2026-08-20",
            "appointment_time": "09:00",
            "confirmation_token": "lab-token-456",
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=201, json=Mock(return_value=booking_response))
        )

        booking = service.create_booking(
            patient_id=patient_id,
            test_ids=test_ids,
            branch_id=branch_id,
            preferred_date="2026-08-20",
        )

        assert booking["status"] == "confirmed"
        assert "booking_id" in booking


class TestCustomerCareFlow:
    """Test customer care support ticket flow."""

    def test_customer_care_ticket_workflow(self, labos_client):
        """Complete customer care ticket workflow."""
        phone = "919999999999"

        # Step 1: Create support ticket
        ticket_response = {
            "ticket_id": str(uuid.uuid4()),
            "status": "created",
            "assigned_to": None,
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=201, json=Mock(return_value=ticket_response))
        )

        service = CustomerCareService(store=None, labos_client=labos_client)
        ticket = service.create_request(
            phone=phone,
            message="I have a question about my bill",
            category="billing",
        )

        assert "ticket_id" in ticket
        assert ticket["status"] == "created"

        # Step 2: Get tickets for patient
        patient_id = phone
        tickets_response = {
            "tickets": [ticket],
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=tickets_response))
        )

        tickets = labos_client.get_customer_care_tickets(patient_id=patient_id)

        assert len(tickets["tickets"]) >= 1
        assert tickets["tickets"][0]["ticket_id"] == ticket["ticket_id"]

    def test_customer_care_fallback_to_local_store(self, labos_client):
        """Customer care falls back to local store if LabOS unavailable."""
        phone = "919999999999"
        patient_id = str(uuid.uuid4())

        # Simulate LabOS error by mocking create_customer_care_ticket to raise
        labos_client.create_customer_care_ticket = Mock(
            side_effect=LabOSClientError("LabOS unavailable")
        )

        # Mock local store
        local_store = Mock()
        local_store.create_support_ticket = Mock(return_value=True)

        service = CustomerCareService(store=local_store, labos_client=labos_client)

        ticket = service.create_request(
            phone=phone,
            message="Support request",
            category="general",
            patient_id=patient_id,
        )

        assert ticket is True  # Boolean response for local fallback
        local_store.create_support_ticket.assert_called_once()


class TestReportDeliveryEnd2End:
    """Test complete report delivery flow from LabOS to WhatsApp."""

    def test_full_report_flow(self, labos_client):
        """Full end-to-end report flow: metadata → results → secure link."""
        report_id = str(uuid.uuid4())
        patient_id = str(uuid.uuid4())

        # Step 1: Get report metadata
        metadata_response = {
            "report_id": report_id,
            "patient_id": patient_id,
            "status": "verified",
            "created_at": "2026-08-17T10:00:00Z",
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=metadata_response))
        )

        metadata = labos_client.get_report_metadata(report_id)
        assert metadata["status"] == "verified"

        # Step 2: Get verified results
        results_response = {
            "report_id": report_id,
            "tests": [
                {
                    "test_name": "Hemoglobin",
                    "result_value": "14.5",
                    "unit": "g/dL",
                    "reference_range": "12-15",
                    "flag": "normal",
                },
            ],
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=results_response))
        )

        results = labos_client.get_verified_results(report_id)
        assert len(results["tests"]) >= 1

        # Step 3: Generate secure link
        link_response = {
            "token": "secure-token-abc",
            "expires_at": "2026-08-18T10:00:00Z",
            "url": "http://localhost:8000/api/v1/public/reports/access/secure-token-abc",
        }
        labos_client.session.request = Mock(
            return_value=Mock(status_code=200, json=Mock(return_value=link_response))
        )

        report = {"report_id": report_id, "patient_id": patient_id}
        access_service = ReportAccessService(Mock(), labos_client=labos_client)
        url = access_service.get_patient_facing_url(report)

        assert "secure-token-abc" in url

    def test_report_not_yet_verified_error_handling(self, labos_client):
        """System handles report not yet verified (409) error."""
        report_id = str(uuid.uuid4())

        # Mock 409 response for unverified report
        labos_client.session.request = Mock(return_value=Mock(status_code=409))

        with pytest.raises(LabOSClientError, match="not yet verified"):
            labos_client.get_verified_results(report_id)
