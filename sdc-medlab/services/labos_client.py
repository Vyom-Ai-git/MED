from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests


logger = logging.getLogger(__name__)


class LabOSConfigError(RuntimeError):
    pass


class LabOSClientError(RuntimeError):
    pass


class LabOSContractNotReady(NotImplementedError):
    pass


@dataclass(slots=True)
class LabOSResponse:
    status_code: int
    content: bytes
    headers: dict[str, str]


class LabOSClient:
    def __init__(self, config, session: requests.Session | None = None):
        self.config = config
        self.session = session or requests.Session()
        self.timeout = config.labos_timeout_seconds
        self.max_retries = config.labos_max_retries

    def _ensure_ready(self) -> None:
        if not self.config.labos_base_url:
            raise LabOSConfigError("LABOS_BASE_URL is not configured")
        if not self.config.labos_integration_key:
            raise LabOSConfigError("LABOS_INTEGRATION_KEY is not configured")

    def _url(self, path: str) -> str:
        base = self.config.labos_base_url.rstrip("/")
        return f"{base}/{path.lstrip('/')}"

    def _headers(self) -> dict[str, str]:
        return {
            "X-Integration-Key": self.config.labos_integration_key,
            "Accept": "application/json, application/pdf",
        }

    def _request(self, method: str, path: str, *, stream: bool = False) -> requests.Response:
        self._ensure_ready()
        url = self._url(path)
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=self._headers(),
                    timeout=self.timeout,
                    stream=stream,
                )
                if response.status_code >= 500:
                    last_error = LabOSClientError(f"LabOS server error HTTP {response.status_code}")
                    if attempt < self.max_retries:
                        time.sleep(min(0.25 * attempt, 1.0))
                        continue
                return response
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(0.25 * attempt, 1.0))
                    continue
            break
        if last_error:
            raise LabOSClientError(str(last_error)) from last_error
        raise LabOSClientError("LabOS request failed unexpectedly")

    def _json(self, method: str, path: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_ready()
        response = self.session.request(
            method,
            self._url(path),
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        if response.status_code in {400, 401, 403, 404, 409}:
            raise LabOSClientError(f"LabOS returned HTTP {response.status_code}")
        if response.status_code >= 500:
            raise LabOSClientError(f"LabOS server error HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise LabOSClientError("LabOS returned invalid JSON") from exc

    def test_webhook(self, webhook_url: str) -> dict[str, Any]:
        """Test n8n webhook integration.
        
        POST /api/v1/integrations/n8n/test
        """
        return self._json("POST", "/api/v1/integrations/n8n/test", payload={"webhook_url": webhook_url})

    def get_integration_logs(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """Get integration event logs.
        
        GET /api/v1/integrations/logs?limit=50&offset=0
        """
        path = f"/api/v1/integrations/logs?limit={limit}&offset={offset}"
        return self._json("GET", path)

    def get_report_metadata(self, report_id: str) -> dict[str, Any]:
        """Get report metadata.
        
        GET /api/v1/integrations/reports/{id}/metadata
        """
        return self._json("GET", f"/api/v1/integrations/reports/{report_id}/metadata")

    def get_verified_results(self, report_id: str) -> dict[str, Any]:
        """Get verified report results.
        
        GET /api/v1/integrations/reports/{id}/results
        Precondition: Report must be in 'verified' status (HTTP 409 if not)
        """
        response = self.session.request(
            "GET",
            self._url(f"/api/v1/integrations/reports/{report_id}/results"),
            headers=self._headers(),
            timeout=self.timeout,
        )
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as exc:
                raise LabOSClientError("LabOS returned invalid JSON") from exc
        if response.status_code == 409:
            raise LabOSClientError(f"Report not yet verified (HTTP {response.status_code})")
        if response.status_code in {401, 404}:
            raise LabOSClientError(f"LabOS returned HTTP {response.status_code}")
        raise LabOSClientError(f"Unexpected LabOS response HTTP {response.status_code}")

    def download_report(self, report_id: str) -> LabOSResponse:
        """Download report PDF.
        
        GET /api/v1/integrations/reports/{id}/download
        """
        response = self._request("GET", f"/api/v1/integrations/reports/{report_id}/download", stream=True)
        if response.status_code == 200:
            return LabOSResponse(
                status_code=response.status_code,
                content=response.content,
                headers=dict(response.headers),
            )
        if response.status_code in {401, 403, 404, 409}:
            raise LabOSClientError(f"LabOS returned HTTP {response.status_code}")
        raise LabOSClientError(f"Unexpected LabOS download response HTTP {response.status_code}")

    def get_patient(self, patient_id: str) -> dict[str, Any]:
        """Patient contact lookup.
        
        GET /api/v1/patients/lookup?patient_id={id}
        """
        path = f"/api/v1/patients/lookup?patient_id={patient_id}"
        return self._json("GET", path)

    def get_secure_link(self, report_id: str, patient_id: str, expires_in_hours: int = 24) -> dict[str, Any]:
        """Generate secure patient-facing report link.
        
        POST /api/v1/reports/{id}/secure-link
        """
        payload = {
            "patient_id": patient_id,
            "expires_in_hours": expires_in_hours,
        }
        return self._json("POST", f"/api/v1/reports/{report_id}/secure-link", payload=payload)

    def get_test_catalog(self) -> dict[str, Any]:
        """Get available test catalog.
        
        GET /api/v1/tests/catalog
        """
        return self._json("GET", "/api/v1/tests/catalog")

    def get_branch_availability(self, city: str | None = None) -> dict[str, Any]:
        """Get branch/location availability.
        
        GET /api/v1/branches/availability[?city=...]
        """
        path = "/api/v1/branches/availability"
        if city:
            path = f"{path}?city={city}"
        return self._json("GET", path)

    def get_doctor_availability(
        self, doctor_id: str, from_date: str | None = None, to_date: str | None = None
    ) -> dict[str, Any]:
        """Get doctor availability.
        
        GET /api/v1/doctors/{id}/availability[?from_date=...&to_date=...]
        """
        path = f"/api/v1/doctors/{doctor_id}/availability"
        params = []
        if from_date:
            params.append(f"from_date={from_date}")
        if to_date:
            params.append(f"to_date={to_date}")
        if params:
            path = f"{path}?{'&'.join(params)}"
        return self._json("GET", path)

    def create_doctor_appointment(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create doctor appointment booking.
        
        POST /api/v1/bookings/doctor
        """
        return self._json("POST", "/api/v1/bookings/doctor", payload=payload)

    def create_lab_booking(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create lab booking.
        
        POST /api/v1/bookings/lab
        """
        return self._json("POST", "/api/v1/bookings/lab", payload=payload)

    def create_customer_care_ticket(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create customer care support ticket.
        
        POST /api/v1/customer-care/handoff
        """
        return self._json("POST", "/api/v1/customer-care/handoff", payload=payload)

    def get_customer_care_tickets(self, patient_id: str | None = None) -> dict[str, Any]:
        """Get customer care tickets.
        
        GET /api/v1/customer-care/handoff[?patient_id=...]
        """
        path = "/api/v1/customer-care/handoff"
        if patient_id:
            path = f"{path}?patient_id={patient_id}"
        return self._json("GET", path)
