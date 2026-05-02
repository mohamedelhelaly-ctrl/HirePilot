from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from models import InterviewType, InterviewStatus

class InterviewSessionBase(BaseModel):
    interview_type: InterviewType
    scheduled_start_time: Optional[datetime] = None
    scheduled_end_time: Optional[datetime] = None


class InterviewSessionCreate(InterviewSessionBase):
    application_id: int
    interviewer_id: Optional[int] = None
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
    interviewer_id: Optional[int]
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