from __future__ import annotations

from datetime import datetime, timezone
from datetime import timedelta
from uuid import uuid4
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MongoStore:
    def __init__(self, config, client: MongoClient | None = None):
        self.config = config
        self.client = client or MongoClient(config.mongodb_uri, serverSelectionTimeoutMS=3000)
        self.db = self.client[config.mongodb_database]

    def ensure_indexes(self) -> None:
        self.db.processed_messages.create_index([("message_id", ASCENDING)], unique=True)
        self.db.reports.create_index([("report_id", ASCENDING)], unique=True, sparse=True)
        self.db.reports.create_index([("report_uuid", ASCENDING)], unique=True, sparse=True)
        self.db.reports.create_index([("phone", ASCENDING), ("report_date", ASCENDING)])
        self.db.conversation_state.create_index([("phone", ASCENDING)], unique=True)
        self.db.labos_events.create_index([("event_id", ASCENDING)], unique=True)
        self.db.appointments.create_index([("booking_id", ASCENDING)], unique=True, sparse=True)
        self.db.doctor_consultations.create_index([("consultation_id", ASCENDING)], unique=True, sparse=True)
        self.db.support_requests.create_index([("ticket_id", ASCENDING)], unique=True, sparse=True)
        self.db.event_logs.create_index([("timestamp", ASCENDING)])

    def ping(self) -> None:
        self.client.admin.command("ping")

    def log_event(
        self,
        event: str,
        phone: str | None = None,
        report_id: str | None = None,
        component: str | None = None,
        status: str | None = None,
        conversation_id: str | None = None,
        message_id: str | None = None,
        workflow: str | None = None,
        state: str | None = None,
        processing_ms: int | None = None,
        error_code: str | None = None,
        error_category: str | None = None,
    ) -> None:
        self.db.event_logs.insert_one(
            {
                "event": event,
                "phone": phone,
                "report_id": report_id,
                "workflow/component": component,
                "status": status,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "workflow": workflow,
                "state": state,
                "timestamp": utcnow(),
                "processing_ms": processing_ms,
                "error_code": error_code,
                "error_category": error_category,
            }
        )

    def mark_processed_message(self, message_id: str, phone: str, message_type: str) -> bool:
        try:
            self.db.processed_messages.insert_one(
                {
                    "message_id": message_id,
                    "phone": phone,
                    "received_at": utcnow(),
                    "message_type": message_type,
                }
            )
            return True
        except DuplicateKeyError:
            return False

    def get_state(self, phone: str) -> dict[str, Any]:
        state = self.db.conversation_state.find_one({"phone": phone})
        if state:
            state.pop("_id", None)
            return state
        expires_at = utcnow() + timedelta(minutes=self.config.session_timeout_minutes)
        return {
            "session_id": str(uuid4()),
            "phone": phone,
            "state": "idle",
            "language": "en",
            "selected_option": None,
            "active_report_id": None,
            "updated_at": utcnow(),
            "expires_at": expires_at,
        }

    def state_expired(self, state: dict[str, Any]) -> bool:
        expires_at = state.get("expires_at")
        if not expires_at:
            return False
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                return False
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at = expires_at.astimezone(timezone.utc)
        return expires_at <= utcnow()

    def set_state(
        self,
        phone: str,
        state: str,
        language: str = "en",
        active_report_id: str | None = None,
        selected_option: str | None = None,
    ) -> None:
        current = self.get_state(phone)
        session_id = current.get("session_id") or str(uuid4())
        expires_at = utcnow() + timedelta(minutes=self.config.session_timeout_minutes)
        self.db.conversation_state.update_one(
            {"phone": phone},
            {
                "$set": {
                    "session_id": session_id,
                    "phone": phone,
                    "state": state,
                    "language": language,
                    "active_report_id": active_report_id,
                    "selected_option": selected_option,
                    "updated_at": utcnow(),
                    "expires_at": expires_at,
                }
            },
            upsert=True,
        )

    def reset_state(self, phone: str) -> None:
        self.set_state(phone, "idle", language="en", active_report_id=None, selected_option=None)

    def set_language(self, phone: str, language: str) -> None:
        current = self.get_state(phone)
        self.set_state(
            phone,
            current.get("state", "idle"),
            language=language,
            active_report_id=current.get("active_report_id"),
            selected_option=current.get("selected_option"),
        )

    def get_report_by_phone_and_id(self, phone: str, report_id: str | None) -> dict[str, Any] | None:
        if not report_id:
            return None
        report = self.db.reports.find_one({"phone": phone, "report_id": report_id})
        if report:
            report.pop("_id", None)
        return report

    def get_latest_report_by_phone(self, phone: str) -> dict[str, Any] | None:
        report = self.db.reports.find_one({"phone": phone}, sort=[("created_at", -1)])
        if report:
            report.pop("_id", None)
        return report

    def upsert_report(self, report_doc: dict[str, Any]) -> None:
        self.db.reports.update_one(
            {"report_id": report_doc["report_id"]},
            {"$setOnInsert": report_doc, "$set": {"updated_at": utcnow()}},
            upsert=True,
        )

    def update_report(self, report_id: str, updates: dict[str, Any]) -> None:
        self.db.reports.update_one({"report_id": report_id}, {"$set": updates})

    def create_appointment(self, appointment: dict[str, Any]) -> bool:
        if self.db.appointments.find_one({"phone": appointment["phone"], "status": {"$in": ["requested", "pending", "confirmed"]}}):
            return False
        try:
            self.db.appointments.insert_one(appointment)
            return True
        except DuplicateKeyError:
            return False

    def create_consultation(self, consultation: dict[str, Any]) -> bool:
        if self.db.doctor_consultations.find_one({"phone": consultation["phone"], "status": {"$in": ["requested", "pending", "confirmed"]}}):
            return False
        try:
            self.db.doctor_consultations.insert_one(consultation)
            return True
        except DuplicateKeyError:
            return False

    def create_support_ticket(self, ticket: dict[str, Any]) -> bool:
        if self.db.support_requests.find_one({"phone": ticket["phone"], "status": {"$in": ["open", "pending"]}}):
            return False
        try:
            self.db.support_requests.insert_one(ticket)
            return True
        except DuplicateKeyError:
            return False

    def report_exists(self, report_id: str, report_uuid: str | None = None) -> bool:
        if self.db.reports.find_one({"report_id": report_id}) is not None:
            return True
        if report_uuid and self.db.reports.find_one({"report_uuid": report_uuid}) is not None:
            return True
        return False

    def insert_labos_event(self, event_doc: dict[str, Any]) -> bool:
        try:
            self.db.labos_events.insert_one(event_doc)
            return True
        except DuplicateKeyError:
            return False

    def get_labos_event(self, event_id: str) -> dict[str, Any] | None:
        event = self.db.labos_events.find_one({"event_id": event_id})
        if event:
            event.pop("_id", None)
        return event

    def update_labos_event(self, event_id: str, updates: dict[str, Any]) -> None:
        self.db.labos_events.update_one({"event_id": event_id}, {"$set": updates})
