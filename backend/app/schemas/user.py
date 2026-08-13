from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.enums import UserRole, UserStatus

class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole = UserRole.TECHNICIAN

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    organization_id: int
    branch_id: Optional[int] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    branch_id: Optional[int] = None
    password: Optional[str] = Field(None, min_length=6)

class UserResponse(BaseModel):
    id: int
    organization_id: int
    branch_id: Optional[int] = None
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole
    status: UserStatus
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
