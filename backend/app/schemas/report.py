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


class ReportMetadataResponse(BaseModel):
    id: int
    report_number: str
    organization_id: int
    branch_id: Optional[int] = None
    order_id: int
    order_number: str
    patient_id: int
    patient_mrn: str
    patient_name: str
    patient_phone: str
    status: str
    version: int
    file_name: str
    file_size: int
    mime_type: str
    checksum: str
    page_count: int = 1
    generated_at: datetime
    generated_by_name: Optional[str] = None
    verification_status: str = "Verified"
    verified_by_pathologist: Optional[str] = None
    verified_at: Optional[datetime] = None
    download_url: str

    model_config = ConfigDict(from_attributes=True)


class VerifiedResultItem(BaseModel):
    test_code: str
    test_name: str
    parameter_name: str
    result_value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    flag: Optional[str] = None  # Normal, High, Low, Critical
    status: str
    technician_name: Optional[str] = None
    pathologist_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VerifiedReportResultsResponse(BaseModel):
    report_id: int
    report_number: str
    order_id: int
    order_number: str
    patient_id: int
    patient_name: str
    patient_mrn: str
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    overall_status: str
    results: List[VerifiedResultItem]

    model_config = ConfigDict(from_attributes=True)


class SecureTokenResponse(BaseModel):
    report_id: int
    report_number: str
    secure_token: str
    expires_at: datetime
    access_url: str

