from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    ordering_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    order_number = Column(String, unique=True, index=True, nullable=False)  # e.g. ORD-2026-00001
    status = Column(String, default="Pending", nullable=False)
    # Controlled states: Pending → Sample Collected → Processing → Result Entered → Verified → Published → Cancelled
    payment_status = Column(String, default="Pending", nullable=False)  # Pending, Paid, Partial, Refunded

    subtotal = Column(Numeric(10, 2), nullable=False, default=0.00)       # Sum of all item unit prices
    discount = Column(Numeric(10, 2), nullable=False, default=0.00)        # Fixed discount amount
    tax = Column(Numeric(10, 2), nullable=False, default=0.00)             # Tax amount
    total_amount = Column(Numeric(10, 2), nullable=False, default=0.00)    # subtotal - discount + tax

    notes = Column(Text, nullable=True)  # Reception notes on the order

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="orders")
    branch = relationship("Branch", back_populates="orders")
    patient = relationship("Patient", back_populates="orders")
    ordering_user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    samples = relationship("Sample", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="SET NULL"), nullable=True)  # nullable: test may be deleted later

    # Price snapshot — protects historical order integrity
    test_name_snapshot = Column(String, nullable=False)   # e.g. "Complete Blood Count"
    test_code_snapshot = Column(String, nullable=False)   # e.g. "CBC"
    unit_price = Column(Numeric(10, 2), nullable=False, default=0.00)  # Price at time of ordering
    quantity = Column(Integer, nullable=False, default=1)
    discount = Column(Numeric(10, 2), nullable=False, default=0.00)  # Per-item discount if any
    total = Column(Numeric(10, 2), nullable=False, default=0.00)  # unit_price * quantity - discount

    status = Column(String, default="Pending", nullable=False)  # Pending, Processing, Completed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    test = relationship("Test", back_populates="order_items")
