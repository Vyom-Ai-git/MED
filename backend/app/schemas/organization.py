from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    contact_info: Optional[Dict[str, Any]] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    contact_info: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class OrganizationResponse(OrganizationBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
