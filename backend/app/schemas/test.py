from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

class TestParameterBase(BaseModel):
    name: str
    code: str
    unit: Optional[str] = None
    data_type: str = "numeric" # numeric, text, select
    reference_range: Optional[str] = None
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    ref_gender: Optional[str] = None
    ref_age_min: Optional[int] = None
    ref_age_max: Optional[int] = None
    ref_context: Optional[str] = None
    critical_config: Optional[Dict[str, Any]] = None
    display_order: int = 0

class TestParameterCreate(TestParameterBase):
    pass

class TestParameterResponse(TestParameterBase):
    id: int
    test_id: int

    model_config = ConfigDict(from_attributes=True)


class TestBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=20)
    name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=50) # Hematology, Biochemistry, etc.
    description: Optional[str] = None
    price: Decimal = Decimal("0.00")

class TestCreate(TestBase):
    organization_id: int
    parameters: Optional[List[TestParameterCreate]] = None

class TestUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    status: Optional[str] = None
    parameters: Optional[List[TestParameterCreate]] = None

class TestResponse(TestBase):
    id: int
    organization_id: int
    status: str
    parameters: List[TestParameterResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TestListResponse(BaseModel):
    items: List[TestResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)
