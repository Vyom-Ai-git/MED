from __future__ import annotations

import logging
import uuid
from typing import Any

from services.labos_client import LabOSClient, LabOSClientError


logger = logging.getLogger(__name__)


class DoctorBookingService:
    """Manage doctor appointment bookings via LabOS API."""

    def __init__(self, labos_client: LabOSClient):
        self.labos_client = labos_client

    def get_available_dates(self, doctor_id: str) -> list[str]:
        """Get available dates for a doctor.
        
        Calls: GET /api/v1/doctors/{id}/availability
        Returns: List of dates (YYYY-MM-DD format)
        """
        try:
            response = self.labos_client.get_doctor_availability(doctor_id)
            slots = response.get("available_slots", [])
            dates = sorted(set(slot.get("date") for slot in slots if slot.get("date")))
            return dates
        except LabOSClientError as exc:
            logger.error(f"Failed to get doctor {doctor_id} available dates: {exc}")
            raise

    def get_available_slots(self, doctor_id: str, date: str) -> list[dict[str, str]]:
        """Get available time slots for a doctor on a specific date.
        
        Args:
            doctor_id: Doctor UUID
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of slot dicts with 'start_time', 'end_time'
        """
        try:
            response = self.labos_client.get_doctor_availability(doctor_id, from_date=date, to_date=date)
            slots = response.get("available_slots", [])
            date_slots = [s for s in slots if s.get("date") == date]
            return date_slots
        except LabOSClientError as exc:
            logger.error(f"Failed to get doctor {doctor_id} slots for {date}: {exc}")
            raise

    def create_booking(self, doctor_id: str, patient_id: str, date: str, time: str) -> dict[str, Any]:
        """Create a doctor appointment booking.
        
        Calls: POST /api/v1/bookings/doctor
        
        Args:
            doctor_id: Doctor UUID
            patient_id: Patient UUID
            date: Appointment date (YYYY-MM-DD)
            time: Appointment time (HH:MM)
            
        Returns:
            Booking response dict with 'appointment_id', 'status', 'confirmation_token'
        """
        payload = {
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "appointment_date": date,
            "appointment_time": time,
        }
        try:
            response = self.labos_client.create_doctor_appointment(payload)
            logger.info(f"Doctor appointment booked: {response.get('appointment_id')}")
            return response
        except LabOSClientError as exc:
            logger.error(f"Failed to create doctor booking: {exc}")
            raise

    def cancel_booking(self, booking_id: str) -> bool:
        """Cancel a doctor appointment booking.
        
        Note: LabOS API does not expose a cancel endpoint in this contract.
        This method is a placeholder for future implementation.
        """
        raise NotImplementedError("DOCTOR_BOOKING_CANCEL_API_NOT_PROVIDED")


class LabBookingService:
    """Manage lab test bookings via LabOS API."""

    def __init__(self, labos_client: LabOSClient):
        self.labos_client = labos_client

    def get_tests(self) -> dict[str, Any]:
        """Get available lab tests.
        
        Calls: GET /api/v1/tests/catalog
        
        Returns:
            Catalog dict with 'tests' array
        """
        try:
            catalog = self.labos_client.get_test_catalog()
            logger.info(f"Retrieved test catalog with {len(catalog.get('tests', []))} tests")
            return catalog
        except LabOSClientError as exc:
            logger.error(f"Failed to get test catalog: {exc}")
            raise

    def get_packages(self) -> list[dict[str, Any]]:
        """Get lab test packages.
        
        Note: Not directly exposed by LabOS API. This is a placeholder.
        """
        raise NotImplementedError("LAB_PACKAGES_API_NOT_PROVIDED")

    def get_branches(self, city: str | None = None) -> dict[str, Any]:
        """Get available lab branches.
        
        Calls: GET /api/v1/branches/availability[?city=...]
        
        Args:
            city: Optional city filter
            
        Returns:
            Availability dict with 'branches' array
        """
        try:
            availability = self.labos_client.get_branch_availability(city=city)
            logger.info(f"Retrieved {len(availability.get('branches', []))} branches")
            return availability
        except LabOSClientError as exc:
            logger.error(f"Failed to get branch availability: {exc}")
            raise

    def get_available_slots(self, branch_id: str, test_ids: list[str]) -> list[dict[str, Any]]:
        """Get available appointment slots for a lab branch.
        
        Note: LabOS API does not provide a dedicated slots endpoint. 
        This is a placeholder for future implementation.
        """
        raise NotImplementedError("LAB_AVAILABLE_SLOTS_API_NOT_PROVIDED")

    def create_booking(self, patient_id: str, test_ids: list[str], branch_id: str, **kwargs) -> dict[str, Any]:
        """Create a lab booking.
        
        Calls: POST /api/v1/bookings/lab
        
        Args:
            patient_id: Patient UUID
            test_ids: List of test UUIDs
            branch_id: Branch UUID
            **kwargs: Optional fields (preferred_date, preferred_time, notes)
            
        Returns:
            Booking response dict with 'booking_id', 'status', 'confirmation_token'
        """
        payload = {
            "patient_id": patient_id,
            "test_ids": test_ids,
            "branch_id": branch_id,
        }
        # Add optional fields if provided
        if "preferred_date" in kwargs and kwargs["preferred_date"]:
            payload["preferred_date"] = kwargs["preferred_date"]
        if "preferred_time" in kwargs and kwargs["preferred_time"]:
            payload["preferred_time"] = kwargs["preferred_time"]
        if "notes" in kwargs and kwargs["notes"]:
            payload["notes"] = kwargs["notes"]

        try:
            response = self.labos_client.create_lab_booking(payload)
            logger.info(f"Lab booking created: {response.get('booking_id')}")
            return response
        except LabOSClientError as exc:
            logger.error(f"Failed to create lab booking: {exc}")
            raise


class CustomerCareService:
    """Manage customer care support tickets via LabOS API."""

    def __init__(self, store=None, labos_client: LabOSClient | None = None):
        self.store = store
        self.labos_client = labos_client

    def create_request(
        self, phone: str, message: str, category: str = "general", patient_id: str | None = None
    ) -> bool | dict[str, Any]:
        """Create a customer care support ticket.
        
        Legacy calling convention: create_request(phone, message) -> bool
        New calling convention: create_request(phone, message, category, patient_id) -> dict
        
        Calls: POST /api/v1/customer-care/handoff (via LabOS)
        Falls back to local store if LabOS unavailable
        
        Args:
            phone: Phone number or contact identifier (legacy, also used as primary key)
            message: Support message
            category: One of: billing, appointment, report_query, general
            patient_id: Optional patient UUID (defaults to phone if not provided)
            
        Returns:
            For backward compatibility with existing code: bool if only store available,
            dict if LabOS response available
        """
        if not patient_id:
            patient_id = phone

        payload = {
            "patient_id": patient_id,
            "category": category,
            "message": message,
            "contact_number": phone,  # Always include phone for local compatibility
        }

        # Try LabOS first
        if self.labos_client:
            try:
                response = self.labos_client.create_customer_care_ticket(payload)
                logger.info(f"Customer care ticket created via LabOS: {response.get('ticket_id')}")
                return response
            except LabOSClientError as exc:
                logger.warning(f"LabOS customer care failed, falling back to local: {exc}")

        # Fall back to local store
        if self.store:
            ticket = {
                "ticket_id": str(uuid.uuid4()),
                "phone": phone,  # Keep phone for backward compatibility with existing store queries
                "patient_id": patient_id,
                "category": category,
                "message": message,
                "status": "created",
            }
            success = self.store.create_support_ticket(ticket)
            if success:
                logger.info(f"Customer care ticket created locally: {ticket['ticket_id']}")
                return success  # Return bool for backward compatibility
            return False

        raise RuntimeError("No LabOS client or local store configured")

    def get_tickets(self, patient_id: str | None = None) -> dict[str, Any]:
        """Get customer care tickets.
        
        Calls: GET /api/v1/customer-care/handoff[?patient_id=...]
        
        Args:
            patient_id: Optional patient filter
            
        Returns:
            Response dict with 'tickets' array
        """
        if not self.labos_client:
            raise RuntimeError("LabOSClient not configured")

        try:
            response = self.labos_client.get_customer_care_tickets(patient_id=patient_id)
            logger.info(f"Retrieved {len(response.get('tickets', []))} customer care tickets")
            return response
        except LabOSClientError as exc:
            logger.error(f"Failed to get customer care tickets: {exc}")
            raise
