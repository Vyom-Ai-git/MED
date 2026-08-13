from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


# ── Nested patient summary (avoids deep nesting) ──────────────────────────────

class OrderPatientSummary(BaseModel):
    id: int
    patient_id: str
    first_name: str
    last_name: str
    phone: str
    date_of_birth: date

    model_config = ConfigDict(from_attributes=True)


# ── Nested ordering user summary ──────────────────────────────────────────────

class OrderUserSummary(BaseModel):
    id: int
    name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


# ── Order Item schemas ────────────────────────────────────────────────────────

class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    test_id: Optional[int] = None
    test_name_snapshot: str
    test_code_snapshot: str
    unit_price: Decimal
    quantity: int
    discount: Decimal
    total: Decimal
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Order Create / Update schemas ─────────────────────────────────────────────

class OrderCreate(BaseModel):
    patient_id: int
    branch_id: Optional[int] = None
    selected_test_ids: List[int] = Field(..., min_length=1)
    discount: Decimal = Decimal("0.00")
    tax: Decimal = Decimal("0.00")
    payment_status: str = "Pending"  # Pending, Paid, Partial
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    """Used for status transitions only."""
    status: Optional[str] = None


class PaymentStatusUpdate(BaseModel):
    payment_status: str  # Pending, Paid, Partial, Refunded


# ── Order Response schemas ────────────────────────────────────────────────────

class OrderResponse(BaseModel):
    id: int
    organization_id: int
    branch_id: Optional[int] = None
    order_number: str
    status: str
    payment_status: str
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total_amount: Decimal
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    patient: Optional[OrderPatientSummary] = None
    ordering_user: Optional[OrderUserSummary] = None
    items: List[OrderItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)


# ── Patient orders (for patient profile page) ─────────────────────────────────

class PatientOrderSummary(BaseModel):
    """Lightweight order summary for patient profile page."""
    id: int
    order_number: str
    status: str
    payment_status: str
    total_amount: Decimal
    created_at: datetime
    items: List[OrderItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
