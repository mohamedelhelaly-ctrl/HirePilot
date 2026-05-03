from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
from models import ApplicationStatus
from .candidate_schemas import Candidate
from .screeningResult_schemas import ScreeningResult
from .interviewSession_schemas import InterviewSession

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



# Extended response schemas with relationships

class ApplicationWithCandidate(Application):
    candidate: Candidate


class ApplicationWithDetails(Application):
    candidate: Candidate
    screening_result: Optional[ScreeningResult] = None
    interview_sessions: List[InterviewSession] = []