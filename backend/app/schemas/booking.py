from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

class DoctorAppointmentCreate(BaseModel):
    organization_id: Optional[int] = None
    patient_id: int
    doctor_id: int
    slot_id: Optional[int] = None
    branch_id: Optional[int] = None
    appointment_date: date
    start_time: str
    end_time: str
    consultation_type: str = "in_person"
    notes: Optional[str] = None

class DoctorAppointmentResponse(BaseModel):
    id: int
    organization_id: int
    booking_number: str
    patient_id: int
    doctor_id: int
    doctor_name: str
    doctor_specialty: str
    slot_id: Optional[int] = None
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    appointment_date: date
    start_time: str
    end_time: str
    consultation_type: str
    status: str
    payment_status: str
    fee: Decimal
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabBookingCreate(BaseModel):
    organization_id: Optional[int] = None
    patient_id: int
    branch_id: Optional[int] = None
    booking_type: str = "home_collection"  # home_collection, walk_in
    preferred_date: date
    preferred_slot: str  # e.g. "08:00 AM - 10:00 AM"
    address: Optional[Dict[str, Any]] = None
    tests_requested: List[Any]  # List of test IDs or test names
    notes: Optional[str] = None

class LabBookingResponse(BaseModel):
    id: int
    organization_id: int
    booking_number: str
    patient_id: int
    patient_name: str
    patient_phone: str
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    booking_type: str
    preferred_date: date
    preferred_slot: str
    address: Optional[Dict[str, Any]] = None
    tests_requested: List[Any]
    status: str
    assigned_phlebotomist_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
