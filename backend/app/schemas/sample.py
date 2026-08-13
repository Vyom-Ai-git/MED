from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# --- Sample Schemas ---

class SampleCreate(BaseModel):
    order_id: int
    sample_type: str = Field(..., example="Blood")
    priority: str = Field("Normal", example="Normal")
    notes: Optional[str] = None


class SampleReject(BaseModel):
    rejection_reason: str = Field(..., example="Hemolyzed sample")


class SampleStatusUpdate(BaseModel):
    status: str = Field(..., example="Collected")


import datetime as dt_module

class SamplePatientSummary(BaseModel):
    id: int
    patient_id: str
    first_name: str
    last_name: str
    phone: str
    gender: str
    date_of_birth: dt_module.date

    model_config = ConfigDict(from_attributes=True)


class SampleOrderSummary(BaseModel):
    id: int
    order_number: str
    created_at: datetime
    patient: Optional[SamplePatientSummary] = None
    tests: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class SampleResponse(BaseModel):
    id: int
    organization_id: int
    branch_id: Optional[int] = None
    order_id: int
    sample_identifier: str
    sample_type: str
    collection_status: str
    priority: str
    collected_at: Optional[datetime] = None
    collected_by: Optional[int] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    recollection_required: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    order: Optional[SampleOrderSummary] = None

    model_config = ConfigDict(from_attributes=True)


class SampleListResponse(BaseModel):
    items: List[SampleResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)


# --- Result Schemas ---

class ResultValueIn(BaseModel):
    parameter_id: int
    order_item_id: int
    test_id: int
    raw_value: Optional[str] = None


class ResultDraftSaveIn(BaseModel):
    results: List[ResultValueIn]


class ResultSubmitIn(BaseModel):
    results: List[ResultValueIn]


class ResultResponse(BaseModel):
    id: int
    organization_id: int
    sample_id: int
    order_item_id: int
    test_id: int
    parameter_id: int
    parameter_name: Optional[str] = None
    parameter_code: Optional[str] = None
    data_type: Optional[str] = None
    raw_value: Optional[str] = None
    numeric_value: Optional[Decimal] = None
    text_value: Optional[str] = None
    unit: Optional[str] = None
    reference_low: Optional[Decimal] = None
    reference_high: Optional[Decimal] = None
    abnormal_flag: str
    critical_flag: bool
    status: str
    entered_by: Optional[int] = None
    entered_at: Optional[datetime] = None
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    correction_reason: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ResultVerificationCreate(BaseModel):
    reason: Optional[str] = None


class ResultVerificationResponse(BaseModel):
    id: int
    organization_id: int
    sample_id: int
    result_id: Optional[int] = None
    action: str
    performed_by: Optional[int] = None
    performed_by_name: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationQueueItem(BaseModel):
    sample: SampleResponse
    results: List[ResultResponse]
    verifications: List[ResultVerificationResponse] = []
    has_critical: bool = False
    has_abnormal: bool = False
    status_summary: str = "Entered"

    model_config = ConfigDict(from_attributes=True)


class VerificationQueueListResponse(BaseModel):
    items: List[VerificationQueueItem]
    total: int
    page: int
    page_size: int
    pending_count: int = 0
    critical_count: int = 0
    correction_count: int = 0
    verified_today_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SampleResultsResponse(BaseModel):
    sample: SampleResponse
    results: List[ResultResponse]
    verifications: List[ResultVerificationResponse] = []

    model_config = ConfigDict(from_attributes=True)

