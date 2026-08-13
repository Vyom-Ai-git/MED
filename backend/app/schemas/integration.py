from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class OutboundEventPayload(BaseModel):
    event_id: str
    event_type: str
    event_version: str = "1.0"
    timestamp: str
    organization_id: int
    branch_id: Optional[int] = None
    report_id: Optional[int] = None
    report_number: Optional[str] = None
    order_id: Optional[int] = None
    patient_id: Optional[int] = None

class IntegrationStatusResponse(BaseModel):
    is_configured: bool
    webhook_url: Optional[str] = None
    status: str  # Connected, Not Configured, Connection Error
    sent_count: int
    pending_count: int
    failed_count: int
    last_successful_delivery: Optional[datetime] = None
    last_failed_delivery: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class IntegrationDeliveryResponse(BaseModel):
    id: int
    organization_id: int
    event_id: str
    event_type: str
    destination: str
    status: str
    attempts: int
    last_attempt_at: Optional[datetime] = None
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class IntegrationDeliveryListResponse(BaseModel):
    items: List[IntegrationDeliveryResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)

class IntegrationTestResponse(BaseModel):
    success: bool
    event_id: str
    status_code: Optional[int] = None
    message: str
