from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
from .enums import InterviewType, InterviewStatus


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    interviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Interview details
    interview_type = Column(SQLEnum(InterviewType), nullable=False)
    status = Column(SQLEnum(InterviewStatus), default=InterviewStatus.SCHEDULED, nullable=False)
    
    # Scheduling
    scheduled_start_time = Column(DateTime(timezone=True))
    scheduled_end_time = Column(DateTime(timezone=True))
    actual_start_time = Column(DateTime(timezone=True))
    actual_end_time = Column(DateTime(timezone=True))
    
    # Calendar integration
    google_calendar_event_id = Column(String(500))
    google_meet_link = Column(String(1000))
    
    # Pre-generated questions
    questions = Column(JSON)  # Array of question strings
    
    # Transcript
    full_transcript = Column(Text)
    
    # Post-interview summary
    summary = Column(Text)
    overall_assessment = Column(Text)
    key_strengths = Column(JSON)  # Array of strings
    key_concerns = Column(JSON)  # Array of strings
    recommendation_score = Column(Float)  # 0-10 scale
    technical_depth_score = Column(Float)  # For technical interviews only
    
    # Follow-up questions generated during interview
    generated_followup_questions = Column(JSON)  # Array of question strings with timestamps
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="interview_sessions")
    interviewer = relationship("User", back_populates="conducted_interviews")
    transcript_chunks = relationship("TranscriptChunk", back_populates="session", cascade="all, delete-orphan")
