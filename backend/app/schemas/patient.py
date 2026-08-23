from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import date, datetime

class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    date_of_birth: date
    gender: str = Field(..., description="male, female, other")
    phone: str = Field(..., min_length=5, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[Dict[str, Any]] = None
    emergency_contact: Optional[Dict[str, Any]] = None
    referring_provider: Optional[str] = None
    communication_preference: str = "email" # whatsapp, email, sms
    consent_operational: bool = True
    consent_promotional: bool = False

class PatientCreate(PatientBase):
    organization_id: int
    patient_id: Optional[str] = None # Will generate automatically if empty
    ignore_duplicate: Optional[bool] = False

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[Dict[str, Any]] = None
    emergency_contact: Optional[Dict[str, Any]] = None
    referring_provider: Optional[str] = None
    communication_preference: Optional[str] = None
    consent_operational: Optional[bool] = None
    consent_promotional: Optional[bool] = None

class PatientResponse(PatientBase):
    id: int
    organization_id: int
    patient_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PatientListResponse(BaseModel):
    items: List[PatientResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)

class PatientLookupResponse(BaseModel):
    id: int
    patient_id: str
    first_name: str
    last_name: str
    full_name: str
    date_of_birth: date
    gender: str
    phone: str
    email: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    communication_preference: str
    consent_operational: bool
    consent_promotional: bool
    recent_orders_count: int = 0

    model_config = ConfigDict(from_attributes=True)

