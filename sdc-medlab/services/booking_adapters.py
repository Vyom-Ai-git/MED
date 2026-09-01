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

    def get_doctors(self, specialty: str | None = None, branch_id: int | None = None, q: str | None = None) -> list[dict[str, Any]]:
        """Get list of doctors from LabOS."""
        try:
            response = self.labos_client.get_doctors(specialty=specialty, branch_id=branch_id, q=q)
            if isinstance(response, dict):
                return response.get("items", [])
            return response if isinstance(response, list) else []
        except LabOSClientError as exc:
            logger.error(f"Failed to get doctors list: {exc}")
            return []

    def get_available_dates(self, doctor_id: str | int) -> list[str]:
        """Get available dates for a doctor."""
        try:
            response = self.labos_client.get_doctor_availability(doctor_id)
            slots = response.get("available_slots", [])
            dates = sorted(set(slot.get("slot_date") or slot.get("date") for slot in slots if slot.get("slot_date") or slot.get("date")))
            return [str(d) for d in dates]
        except LabOSClientError as exc:
            logger.error(f"Failed to get doctor {doctor_id} available dates: {exc}")
            return []

    def get_available_slots(self, doctor_id: str | int, slot_date: str) -> list[dict[str, Any]]:
        """Get available time slots for a doctor on a specific date."""
        try:
            response = self.labos_client.get_doctor_availability(doctor_id, slot_date=slot_date)
            slots = response.get("available_slots", [])
            return [s for s in slots if (s.get("slot_date") == slot_date or s.get("date") == slot_date) and not s.get("is_booked")]
        except LabOSClientError as exc:
            logger.error(f"Failed to get doctor {doctor_id} slots for {slot_date}: {exc}")
            return []

    def create_booking(
        self,
        doctor_id: str | int,
        patient_id: str | int,
        date: str,
        start_time: str,
        end_time: str | None = None,
        slot_id: int | str | None = None,
        branch_id: int | str | None = None,
        consultation_type: str = "in_person",
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a doctor appointment booking matching FastAPI DoctorAppointmentCreate schema."""
        if not end_time:
            try:
                hh, mm = map(int, start_time.split(":")[:2])
                end_time = f"{(hh + (mm + 30) // 60) % 24:02d}:{(mm + 30) % 60:02d}"
            except Exception:
                end_time = start_time

        payload: dict[str, Any] = {
            "patient_id": int(patient_id) if str(patient_id).isdigit() else patient_id,
            "doctor_id": int(doctor_id) if str(doctor_id).isdigit() else doctor_id,
            "appointment_date": date,
            "start_time": start_time,
            "end_time": end_time,
            "consultation_type": consultation_type,
        }
        if slot_id and str(slot_id).isdigit():
            payload["slot_id"] = int(slot_id)
        if branch_id and str(branch_id).isdigit():
            payload["branch_id"] = int(branch_id)
        if notes:
            payload["notes"] = notes

        try:
            response = self.labos_client.create_doctor_appointment(payload)
            logger.info(f"Doctor appointment booked: {response.get('booking_number') or response.get('id')}")
            return response
        except LabOSClientError as exc:
            logger.error(f"Failed to create doctor booking: {exc}")
            raise


class LabBookingService:
    """Manage lab test bookings via LabOS API."""

    def __init__(self, labos_client: LabOSClient):
        self.labos_client = labos_client

    def get_tests(self) -> dict[str, Any]:
        """Get available lab test catalog."""
        try:
            catalog = self.labos_client.get_test_catalog()
            items = catalog.get("items", [])
            logger.info(f"Retrieved test catalog with {len(items)} tests")
            return catalog
        except LabOSClientError as exc:
            logger.error(f"Failed to get test catalog: {exc}")
            return {"items": [], "total": 0}

    def get_branches(self, city: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
        """Get available lab branches."""
        try:
            res = self.labos_client.get_branch_availability(city=city)
            if isinstance(res, dict) and "branches" in res:
                return res
            branches = res if isinstance(res, list) else res.get("branches", res.get("items", []))
            logger.info(f"Retrieved {len(branches)} branches")
            return branches
        except LabOSClientError as exc:
            logger.error(f"Failed to get branch availability: {exc}")
            return []

    def create_booking(
        self,
        patient_id: str | int,
        tests_requested: list[str | dict[str, Any]] | str | None = None,
        preferred_date: str = "2026-09-01",
        preferred_slot: str = "Morning (09:00 AM - 12:00 PM)",
        booking_type: str = "home_collection",
        branch_id: int | str | None = None,
        address: dict[str, Any] | str | None = None,
        notes: str | None = None,
        test_ids: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a lab booking matching FastAPI LabBookingCreate schema."""
        raw_tests = tests_requested or test_ids or []
        if isinstance(raw_tests, str):
            raw_tests = [raw_tests]

        payload: dict[str, Any] = {
            "patient_id": int(patient_id) if str(patient_id).isdigit() else patient_id,
            "preferred_date": preferred_date,
            "preferred_slot": preferred_slot,
            "tests_requested": raw_tests,
            "booking_type": booking_type,
        }
        if branch_id and str(branch_id).isdigit():
            payload["branch_id"] = int(branch_id)
        if address:
            if isinstance(address, str):
                payload["address"] = {"street": address}
            else:
                payload["address"] = address
        if notes:
            payload["notes"] = notes

        try:
            response = self.labos_client.create_lab_booking(payload)
            logger.info(f"Lab booking created: {response.get('booking_number') or response.get('id')}")
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
        self,
        phone: str,
        message: str,
        category: str = "report_query",
        patient_id: str | int | None = None,
        order_id: str | int | None = None,
        summary: str | None = None,
    ) -> dict[str, Any] | bool:
        """Create a customer care support ticket matching FastAPI CustomerCareHandoffCreate schema."""
        ticket_summary = summary or message or f"Support request from {phone}"
        payload: dict[str, Any] = {
            "summary": ticket_summary,
            "category": category,
            "channel": "whatsapp",
            "priority": "normal",
        }
        if patient_id and str(patient_id).isdigit():
            payload["patient_id"] = int(patient_id)
        if order_id and str(order_id).isdigit():
            payload["order_id"] = int(order_id)

        if self.labos_client:
            try:
                response = self.labos_client.create_customer_care_ticket(payload)
                logger.info(f"Customer care ticket created via LabOS: {response.get('ticket_number') or response.get('id')}")
                return response
            except LabOSClientError as exc:
                logger.warning(f"LabOS customer care failed, falling back to local: {exc}")

        if self.store:
            ticket = {
                "ticket_id": str(uuid.uuid4()),
                "phone": phone,
                "category": category,
                "summary": ticket_summary,
                "status": "created",
            }
            success = self.store.create_support_ticket(ticket)
            return success

        raise RuntimeError("No LabOS client or local store configured")

    def get_tickets(self, patient_id: str | None = None) -> dict[str, Any]:
        """Get customer care tickets."""
        if not self.labos_client:
            raise RuntimeError("LabOSClient not configured")

        try:
            return self.labos_client.get_customer_care_tickets(patient_id=patient_id)
        except LabOSClientError as exc:
            logger.error(f"Failed to get customer care tickets: {exc}")
            raise
