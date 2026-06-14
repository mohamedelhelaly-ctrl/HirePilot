from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
from models import ApplicationStatus
from .candidate_schemas import Candidate
from .screeningResult_schemas import ScreeningResult
from .interviewSession_schemas import InterviewSession

class ApplicationBase(BaseModel):
    # stated_availability: Optional[Any] = None
    pass


class ApplicationCreate(ApplicationBase):
    candidate_id: int
    requisition_id: int
    lever_opportunity_id: str
    cv_url: Optional[str] = None
    years_of_experience: Optional[float] = None


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    cv_text: Optional[str] = None
    combined_score: Optional[float] = None
    assessment_score: Optional[float] = None
    overall_interview_score: Optional[float] = None
    years_of_experience: Optional[float] = None
    tech_questions: Optional[List[dict[str, str]]] = None


class Application(ApplicationBase):
    id: int
    candidate_id: int
    requisition_id: int
    lever_opportunity_id: str
    status: ApplicationStatus
    cv_url: Optional[str]
    combined_score: Optional[float]
    years_of_experience: Optional[float]
    tech_questions: Optional[List[dict[str, str]]] = None
    interview_scheduled_at: Optional[datetime]
    last_interview_completed_at: Optional[datetime]
    overall_interview_score: Optional[float]
    applied_at: datetime
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime
    justification: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


def application_to_read(app) -> "Application":
    """Map ORM application (+ optional screening_result) to API schema."""
    data = Application.model_validate(app)
    screening = getattr(app, "screening_result", None)
    if screening is not None and screening.justification is not None:
        return data.model_copy(update={"justification": screening.justification})
    return data



# Extended response schemas with relationships

class ApplicationWithCandidate(Application):
    candidate: Candidate


class ApplicationWithDetails(Application):
    candidate: Candidate
    screening_result: Optional[ScreeningResult] = None
    interview_sessions: List[InterviewSession] = []