from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from .database import Base


# Enums
class UserRole(str, enum.Enum):
    HR_MANAGER = "hr_manager"
    HIRING_MANAGER = "hiring_manager"


class ApplicationStatus(str, enum.Enum):
    NEW = "new"
    SCREENING_PENDING = "screening_pending"
    SCREENING_PASSED = "screening_passed"
    SCREENING_REJECTED = "screening_rejected"
    ASSESSMENT_SENT = "assessment_sent"
    ASSESSMENT_COMPLETED = "assessment_completed"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFER_EXTENDED = "offer_extended"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class InterviewType(str, enum.Enum):
    HR_SCREEN = "hr_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    FINAL = "final"


class InterviewStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    assigned_requisitions = relationship("Requisition", back_populates="hiring_manager")
    conducted_interviews = relationship("InterviewSession", back_populates="interviewer")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


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
    
    last_screening_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hiring_manager = relationship("User", back_populates="assigned_requisitions")
    applications = relationship("Application", back_populates="requisition", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    lever_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50))
    linkedin_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")


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
    cv_text = Column(Text)
    cv_embedding_stored = Column(Boolean, default=False, nullable=False)
    
    # Scores
    cosine_similarity_score = Column(Float)  # CV vs. job description similarity
    technical_score = Column(Float)  # AI-generated technical assessment
    behavioral_score = Column(Float)  # AI-generated cultural fit score
    combined_score = Column(Float, index=True)  # Weighted combination
    
    # Assessment data
    assessment_sent_at = Column(DateTime(timezone=True))
    assessment_completed_at = Column(DateTime(timezone=True))
    assessment_score = Column(Float)
    assessment_test_url = Column(String(1000))
    hackerrank_test_id = Column(String(255))
    
    # Interview data
    interview_scheduled_at = Column(DateTime(timezone=True))
    last_interview_completed_at = Column(DateTime(timezone=True))
    overall_interview_score = Column(Float)  # Average across all interviews
    
    # Availability
    stated_availability = Column(JSON)  # Store candidate's preferred time slots
    
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


class ApplicationDetail(Base):
    __tablename__ = "application_details"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    
    # Normalized CV fields for fast filtering
    skill_name = Column(String(255), index=True)
    years_of_experience = Column(Float)
    education_degree = Column(String(255))
    education_institution = Column(String(255))
    previous_company = Column(String(255))
    previous_role = Column(String(255))
    certification = Column(String(255))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="details")


class ScreeningResult(Base):
    __tablename__ = "screening_results"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, unique=True)
    
    # Detailed breakdown
    technical_score = Column(Float, nullable=False)
    behavioral_score = Column(Float, nullable=False)
    technical_justification = Column(Text)
    behavioral_justification = Column(Text)
    overall_justification = Column(Text)
    
    # Recommendations
    recommended_action = Column(String(100))  # "advance", "reject", "needs_review"
    key_strengths = Column(JSON)  # Array of strings
    key_concerns = Column(JSON)  # Array of strings
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="screening_result")


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


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    
    # Transcript content
    text = Column(Text, nullable=False)
    speaker = Column(String(50))  # "interviewer" or "candidate"
    sequence_number = Column(Integer, nullable=False)  # Order of chunks
    
    # Timing
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    offset_seconds = Column(Float)  # Time from interview start
    
    # Relationships
    session = relationship("InterviewSession", back_populates="transcript_chunks")


class StatusHistory(Base):
    __tablename__ = "status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    
    # Status change
    from_status = Column(SQLEnum(ApplicationStatus))
    to_status = Column(SQLEnum(ApplicationStatus), nullable=False)
    
    # Context
    changed_by_user_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(String(500))
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="status_history")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Event identification
    lever_event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    
    # Payload
    payload = Column(JSON, nullable=False)
    
    # Processing status
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processing_error = Column(Text)
    processed_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
