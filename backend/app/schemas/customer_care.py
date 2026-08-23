from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CustomerCareHandoffCreate(BaseModel):
    organization_id: Optional[int] = None
    patient_id: Optional[int] = None
    order_id: Optional[int] = None
    channel: str = "whatsapp"  # whatsapp, phone, chat, web
    category: str = "report_query"  # report_query, delay, booking, billing, other
    priority: str = "normal"  # low, normal, high, urgent
    summary: str = Field(..., min_length=1)
    conversation_transcript: Optional[List[Dict[str, Any]]] = None

class CustomerCareHandoffResponse(BaseModel):
    id: int
    organization_id: int
    ticket_number: str
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    channel: str
    category: str
    priority: str
    summary: str
    conversation_transcript: Optional[List[Dict[str, Any]]] = None
    status: str
    assigned_agent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
