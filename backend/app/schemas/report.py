from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class ReportPatientSummary(BaseModel):
    id: int
    patient_id: str
    first_name: str
    last_name: str
    phone: str
    gender: str

    model_config = ConfigDict(from_attributes=True)


class ReportOrderSummary(BaseModel):
    id: int
    order_number: str
    created_at: datetime
    patient: Optional[ReportPatientSummary] = None
    tests: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class ReportResponse(BaseModel):
    id: int
    organization_id: int
    branch_id: Optional[int] = None
    order_id: int
    patient_id: int
    report_number: str
    status: str
    version: int
    file_name: str
    file_size: int
    mime_type: str
    checksum: str
    generated_at: datetime
    generated_by: Optional[int] = None
    generated_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    order: Optional[ReportOrderSummary] = None
    patient: Optional[ReportPatientSummary] = None

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    items: List[ReportResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)
