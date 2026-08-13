from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    code = Column(String, index=True, nullable=False) # e.g. CBC, HBA1C
    name = Column(String, nullable=False) # e.g. Complete Blood Count
    category = Column(String, nullable=False) # e.g. Hematology, Biochemistry
    description = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    status = Column(String, default="active", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="tests")
    parameters = relationship("TestParameter", back_populates="test", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="test")


class TestParameter(Base):
    __tablename__ = "test_parameters"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False) # e.g. Hemoglobin
    code = Column(String, nullable=False) # e.g. HB
    unit = Column(String, nullable=True) # e.g. g/dL
    data_type = Column(String, default="numeric", nullable=False) # numeric, text, select
    reference_range = Column(String, nullable=True) # e.g. "12.0 - 15.0"
    lower_limit = Column(Numeric(10, 2), nullable=True)
    upper_limit = Column(Numeric(10, 2), nullable=True)
    critical_low = Column(Numeric(10, 2), nullable=True)
    critical_high = Column(Numeric(10, 2), nullable=True)
    ref_gender = Column(String, nullable=True)
    ref_age_min = Column(Integer, nullable=True)
    ref_age_max = Column(Integer, nullable=True)
    ref_context = Column(String, nullable=True)
    critical_config = Column(JSON, nullable=True) # {"low": 7.0, "high": 20.0}
    display_order = Column(Integer, default=0, nullable=False)

    # Relationships
    test = relationship("Test", back_populates="parameters")
