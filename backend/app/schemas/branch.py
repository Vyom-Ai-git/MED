from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class BranchBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    address: Optional[Dict[str, Any]] = None
    contact_info: Optional[Dict[str, Any]] = None

class BranchCreate(BranchBase):
    organization_id: int

class BranchUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    contact_info: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class BranchResponse(BranchBase):
    id: int
    organization_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
