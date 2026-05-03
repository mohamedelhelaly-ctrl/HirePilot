from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .sqlachemy_base import SQLAlchemyBase as Base
from ..tables_enums import ApplicationStatus


class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=False)
    lever_opportunity_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Current status
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.NEW, nullable=False, index=True)
    
    # CV data
    cv_url = Column(String(1000))
    # cv_embedding_stored = Column(Boolean, default=False, nullable=False)
    
    # Scores
    combined_score = Column(Float, index=True)  # Weighted combination
   
    
    # Interview data
    interview_scheduled_at = Column(DateTime(timezone=True))
    last_interview_completed_at = Column(DateTime(timezone=True))
    overall_interview_score = Column(Float)  # Average across all interviews

    
    # Metadata
    applied_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    
    # Relationships
    candidate = relationship("Candidate", back_populates="applications")
    requisition = relationship("Requisition", back_populates="applications")
    details = relationship("ApplicationDetail", back_populates="application", cascade="all, delete-orphan")
    screening_result = relationship("ScreeningResult", back_populates="application", uselist=False, cascade="all, delete-orphan")
    interview_sessions = relationship("InterviewSession", back_populates="application", cascade="all, delete-orphan")
    status_history = relationship("StatusHistory", back_populates="application", cascade="all, delete-orphan")
