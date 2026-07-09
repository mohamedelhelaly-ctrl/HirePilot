from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .sqlachemy_base import SQLAlchemyBase as Base


class Requisition(Base):
    __tablename__ = "requisitions"
    
    id = Column(Integer, primary_key=True, index=True)
    lever_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    department = Column(String(255))
    location = Column(String(255))
    hiring_manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Batch processing counters and thresholds
    new_candidate_counter = Column(Integer, default=0, nullable=False)
    new_candidate_threshold = Column(Integer, default=10, nullable=False)
    new_assessment_counter = Column(Integer, default=0, nullable=False)
    new_assessment_threshold = Column(Integer, default=5, nullable=False)
    new_interview_counter = Column(Integer, default=0, nullable=False)
    new_interview_threshold = Column(Integer, default=3, nullable=False)

    # Screening state — prevents concurrent runs on the same requisition.
    # Set to True before invoking the graph, back to False after completion
    # (whether success or failure). Both the scheduler and the manual trigger
    # endpoint check this flag before firing.
    screening_in_progress = Column(Boolean, default=False, nullable=False)

    last_screening_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hiring_manager = relationship("User", back_populates="assigned_requisitions")
    applications = relationship("Application", back_populates="requisition", cascade="all, delete-orphan")
    chat_threads = relationship("ChatThread", back_populates="requisition", cascade="all, delete-orphan")