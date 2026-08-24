from __future__ import annotations

import logging
from typing import Any

from services.labos_client import LabOSClient, LabOSClientError


logger = logging.getLogger(__name__)


class ReportAccessService:
    """Manage patient-facing report access via LabOS secure link generation."""

    def __init__(self, config, labos_client: LabOSClient | None = None):
        self.config = config
        self.labos_client = labos_client

    def get_patient_facing_url(self, report: dict, expires_in_hours: int = 24) -> str:
        """Generate and return patient-facing report URL via LabOS.
        
        Steps:
        1. Call LabOS POST /api/v1/reports/{id}/secure-link
        2. Extract and return the 'url' field from response
        
        Args:
            report: Report dict with 'report_id' and 'patient_id'
            expires_in_hours: Link expiration time (default 24 hours)
            
        Returns:
            Patient-facing URL string
            
        Raises:
            LabOSClientError: If LabOS secure link generation fails
        """
        if not self.labos_client:
            raise RuntimeError("LabOSClient not configured")

        report_id = report.get("report_id")
        patient_id = report.get("patient_id")

        if not report_id or not patient_id:
            raise ValueError("Report must contain 'report_id' and 'patient_id'")

        try:
            response = self.labos_client.get_secure_link(
                report_id=report_id,
                patient_id=patient_id,
                expires_in_hours=expires_in_hours,
            )
            url = response.get("url")
            if not url:
                raise LabOSClientError("LabOS did not return 'url' in secure link response")
            logger.info(f"Generated secure link for report {report_id}, expires in {expires_in_hours}h")
            return url
        except LabOSClientError as exc:
            logger.error(f"Failed to generate secure link for report {report_id}: {exc}")
            raise

    def describe_unavailable(self) -> str:
        """Return fallback description if secure link generation is unavailable."""
        return (
            "The official report is available through the LabOS-backed delivery flow. "
            "Access the report using the patient-facing link sent to your registered phone number."
        )
