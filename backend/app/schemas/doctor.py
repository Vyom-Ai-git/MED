from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, time, datetime
from decimal import Decimal

class DoctorScheduleSlotBase(BaseModel):
    slot_date: date
    start_time: time
    end_time: time
    consultation_type: str = "in_person"  # in_person, tele_consult
    is_booked: bool = False

class DoctorScheduleSlotCreate(DoctorScheduleSlotBase):
    doctor_id: int
    branch_id: Optional[int] = None

class DoctorScheduleSlotResponse(DoctorScheduleSlotBase):
    id: int
    doctor_id: int
    branch_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DoctorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    specialty: str = Field(..., min_length=1, max_length=100)
    qualification: str
    phone: str
    email: Optional[str] = None
    consultation_fee: Decimal = Decimal("500.00")
    bio: Optional[str] = None
    is_active: bool = True

class DoctorCreate(DoctorBase):
    organization_id: int
    branch_id: Optional[int] = None
    doctor_code: Optional[str] = None

class DoctorResponse(DoctorBase):
    id: int
    organization_id: int
    branch_id: Optional[int] = None
    doctor_code: str
    branch_name: Optional[str] = None
    available_slots_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DoctorListResponse(BaseModel):
    items: List[DoctorResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
