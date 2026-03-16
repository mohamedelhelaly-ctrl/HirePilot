from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


# Enums (matching database enums)
class UserRole(str, Enum):
    HR_MANAGER = "hr_manager"
    HIRING_MANAGER = "hiring_manager"


class ApplicationStatus(str, Enum):
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


class InterviewType(str, Enum):
    HR_SCREEN = "hr_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    FINAL = "final"


class InterviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Base schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ============================================================================
# Request/Response Schemas
# ============================================================================

class GoogleLoginRequest(BaseModel):
    """Google OAuth ID token login request."""
    id_token: str


class TokenRefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str

class LogoutRequest(BaseModel):
    """Request model for logout endpoint."""
    refresh_token: str | None = None


class LogoutResponse(BaseModel):
    """Response model for logout endpoint."""
    message: str



# Requisition schemas
class RequisitionBase(BaseModel):
    title: str
    description: str
    department: Optional[str] = None
    location: Optional[str] = None


class RequisitionCreate(RequisitionBase):
    lever_id: str
    hiring_manager_id: Optional[int] = None


class RequisitionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    hiring_manager_id: Optional[int] = None
    is_active: Optional[bool] = None


class Requisition(RequisitionBase):
    id: int
    lever_id: str
    hiring_manager_id: Optional[int]
    is_active: bool
    new_candidate_counter: int
    new_candidate_threshold: int
    new_assessment_counter: int
    new_assessment_threshold: int
    new_interview_counter: int
    new_interview_threshold: int
    last_screening_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Candidate schemas
class CandidateBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None


class CandidateCreate(CandidateBase):
    lever_id: str


class CandidateUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None


class Candidate(CandidateBase):
    id: int
    lever_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Application schemas
class ApplicationBase(BaseModel):
    stated_availability: Optional[Any] = None


class ApplicationCreate(ApplicationBase):
    candidate_id: int
    requisition_id: int
    lever_opportunity_id: str
    cv_url: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    cv_text: Optional[str] = None
    cosine_similarity_score: Optional[float] = None
    technical_score: Optional[float] = None
    behavioral_score: Optional[float] = None
    combined_score: Optional[float] = None
    assessment_score: Optional[float] = None
    overall_interview_score: Optional[float] = None
    stated_availability: Optional[Any] = None


class Application(ApplicationBase):
    id: int
    candidate_id: int
    requisition_id: int
    lever_opportunity_id: str
    status: ApplicationStatus
    cv_url: Optional[str]
    cv_text: Optional[str]
    cv_embedding_stored: bool
    cosine_similarity_score: Optional[float]
    technical_score: Optional[float]
    behavioral_score: Optional[float]
    combined_score: Optional[float]
    assessment_sent_at: Optional[datetime]
    assessment_completed_at: Optional[datetime]
    assessment_score: Optional[float]
    assessment_test_url: Optional[str]
    hackerrank_test_id: Optional[str]
    interview_scheduled_at: Optional[datetime]
    last_interview_completed_at: Optional[datetime]
    overall_interview_score: Optional[float]
    applied_at: datetime
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ApplicationDetail schemas
class ApplicationDetailBase(BaseModel):
    key: str
    value: Any
    relevance: Optional[str] = None


class ApplicationDetailCreate(ApplicationDetailBase):
    application_id: int


class ApplicationDetail(ApplicationDetailBase):
    id: int
    application_id: int
    extracted_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ScreeningResult schemas
class ScreeningResultBase(BaseModel):
    technical_score: float
    behavioral_score: float
    technical_justification: Optional[str] = None
    behavioral_justification: Optional[str] = None
    overall_justification: Optional[str] = None
    recommended_action: Optional[str] = None
    key_strengths: Optional[List[str]] = None
    key_concerns: Optional[List[str]] = None


class ScreeningResultCreate(ScreeningResultBase):
    application_id: int


class ScreeningResultUpdate(ScreeningResultBase):
    technical_score: Optional[float] = None
    behavioral_score: Optional[float] = None


class ScreeningResult(ScreeningResultBase):
    id: int
    application_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# InterviewSession schemas
class InterviewSessionBase(BaseModel):
    interview_type: InterviewType
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None


class InterviewSessionCreate(InterviewSessionBase):
    application_id: int
    interviewer_id: int
    google_calendar_event_id: Optional[str] = None
    google_meet_link: Optional[str] = None
    questions: Optional[List[str]] = None


class InterviewSessionUpdate(BaseModel):
    status: Optional[InterviewStatus] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    full_transcript: Optional[str] = None
    summary: Optional[str] = None
    overall_assessment: Optional[str] = None
    key_strengths: Optional[List[str]] = None
    key_concerns: Optional[List[str]] = None
    recommendation_score: Optional[float] = None
    technical_depth_score: Optional[float] = None
    generated_followup_questions: Optional[List[Any]] = None


class InterviewSession(InterviewSessionBase):
    id: int
    application_id: int
    interviewer_id: int
    status: InterviewStatus
    actual_start_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    google_calendar_event_id: Optional[str]
    google_meet_link: Optional[str]
    questions: Optional[List[str]]
    full_transcript: Optional[str]
    summary: Optional[str]
    overall_assessment: Optional[str]
    key_strengths: Optional[List[str]]
    key_concerns: Optional[List[str]]
    recommendation_score: Optional[float]
    technical_depth_score: Optional[float]
    generated_followup_questions: Optional[List[Any]]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# TranscriptChunk schemas
class TranscriptChunkBase(BaseModel):
    text: str
    speaker: Optional[str] = None
    sequence_number: int
    offset_seconds: Optional[float] = None


class TranscriptChunkCreate(TranscriptChunkBase):
    session_id: int


class TranscriptChunk(TranscriptChunkBase):
    id: int
    session_id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)


# StatusHistory schemas
class StatusHistoryBase(BaseModel):
    from_status: Optional[ApplicationStatus] = None
    to_status: ApplicationStatus
    reason: Optional[str] = None
    notes: Optional[str] = None


class StatusHistoryCreate(StatusHistoryBase):
    application_id: int
    changed_by_user_id: Optional[int] = None


class StatusHistory(StatusHistoryBase):
    id: int
    application_id: int
    changed_by_user_id: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# WebhookEvent schemas
class WebhookEventBase(BaseModel):
    lever_event_id: str
    event_type: str
    payload: Any


class WebhookEventCreate(WebhookEventBase):
    pass


class WebhookEventUpdate(BaseModel):
    processed: bool
    processing_error: Optional[str] = None
    processed_at: Optional[datetime] = None


class WebhookEvent(WebhookEventBase):
    id: int
    processed: bool
    processing_error: Optional[str]
    processed_at: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Extended response schemas with relationships
class ApplicationWithCandidate(Application):
    candidate: Candidate


class ApplicationWithDetails(Application):
    candidate: Candidate
    screening_result: Optional[ScreeningResult] = None
    interview_sessions: List[InterviewSession] = []


class RequisitionWithApplications(Requisition):
    applications: List[ApplicationWithCandidate] = []


# RAG Chat schemas
class RAGQuery(BaseModel):
    query: str
    requisition_id: Optional[int] = None


class RAGCitation(BaseModel):
    candidate_id: int
    candidate_name: str
    application_id: int
    excerpt: str
    source_type: str  # "cv", "transcript", "assessment"


class RAGResponse(BaseModel):
    answer: str
    citations: List[RAGCitation]


# Assessment schemas
class SendAssessmentRequest(BaseModel):
    application_id: int


class SendAssessmentResponse(BaseModel):
    success: bool
    test_url: str
    message: str


# Interview scheduling schemas
class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime


class AvailabilityRequest(BaseModel):
    application_id: int
    interviewer_id: int
    interview_type: InterviewType


class AvailabilityResponse(BaseModel):
    available_slots: List[TimeSlot]


class ScheduleInterviewRequest(BaseModel):
    application_id: int
    interviewer_id: int
    interview_type: InterviewType
    selected_slot: TimeSlot


class ScheduleInterviewResponse(BaseModel):
    success: bool
    session_id: int
    meet_link: str
    message: str


# Live interview schemas
class StartInterviewRequest(BaseModel):
    session_id: int


class EndInterviewRequest(BaseModel):
    session_id: int


class InterviewSummaryResponse(BaseModel):
    summary: str
    overall_assessment: str
    key_strengths: List[str]
    key_concerns: List[str]
    recommendation_score: float
    technical_depth_score: Optional[float] = None


# WebSocket message schemas
class WSMessage(BaseModel):
    type: str  # "transcript", "followup_question", "error", "update"
    data: Any


# Batch screening trigger
class TriggerScreeningRequest(BaseModel):
    requisition_id: int
    force: bool = False  # Bypass counter threshold check
