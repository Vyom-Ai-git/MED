from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class CustomerCareHandoff(Base):
    __tablename__ = "customer_care_handoffs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    ticket_number = Column(String, unique=True, index=True, nullable=False)  # e.g. TKT-2026-00001
    
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    
    channel = Column(String, default="whatsapp", nullable=False)  # whatsapp, phone, chat, web
    category = Column(String, default="report_query", nullable=False)  # report_query, delay, booking, billing, other
    priority = Column(String, default="normal", nullable=False)  # low, normal, high, urgent
    
    summary = Column(Text, nullable=False)
    conversation_transcript = Column(JSON, nullable=True)  # JSON array of messages
    
    status = Column(String, default="Open", nullable=False)  # Open, In_Progress, Resolved, Closed
    assigned_agent_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    patient = relationship("Patient")
    order = relationship("Order")
    assigned_agent = relationship("User")
