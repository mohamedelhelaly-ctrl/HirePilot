from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, unique=True)

    # Single overall score (0–1 scale, mirrors Application.combined_score)
    score = Column(Float, nullable=False)

    # Single justification covering the candidate's overall fit
    justification = Column(Text)

    # Supporting detail
    recommended_action = Column(String(100))  # "advance" | "reject" | "needs_review"
    key_strengths = Column(JSON)              # List[str]
    key_concerns = Column(JSON)               # List[str]

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    application = relationship("Application", back_populates="screening_result")