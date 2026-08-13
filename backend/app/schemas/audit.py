from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class AuditLogBase(BaseModel):
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    event_type: Optional[str] = None
    description: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    failure_reason: Optional[str] = None


class AuditLogResponse(AuditLogBase):
    id: int
    organization_id: int
    branch_id: Optional[int] = None
    user_id: Optional[int] = None
    created_at: datetime
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
