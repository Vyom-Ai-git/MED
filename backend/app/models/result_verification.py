from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class ResultVerification(Base):
    __tablename__ = "result_verifications"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    sample_id = Column(Integer, ForeignKey("samples.id", ondelete="CASCADE"), nullable=False)
    result_id = Column(Integer, ForeignKey("results.id", ondelete="CASCADE"), nullable=True)

    action = Column(String, nullable=False)  # Submitted, Reviewed, Approved, Returned for Correction
    performed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization")
    sample = relationship("Sample")
    result = relationship("Result")
    actor = relationship("User", foreign_keys=[performed_by])
