"""
Google Calendar API schemas.
Request and response models for calendar endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class InterviewTypeEnum(str, Enum):
    """Valid interview types."""
    HR_SCREEN = "hr_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    FINAL = "final"


class CalendarStatusEnum(str, Enum):
    """Calendar event status."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


# ============================================================================
# Request Schemas
# ============================================================================

class CalendarAvailabilityRequest(BaseModel):
    """Request to check HR manager's calendar availability."""
    date_from: str = Field(..., description="Start date in ISO format (YYYY-MM-DD)")
    date_to: str = Field(..., description="End date in ISO format (YYYY-MM-DD)")
    interview_type: InterviewTypeEnum = Field(..., description="Type of interview")


class ScheduleInterviewRequest(BaseModel):
    """Request to schedule a new interview."""
    candidate_email: EmailStr = Field(..., description="Candidate's email address")
    candidate_name: str = Field(..., description="Candidate's full name")
    application_id: int = Field(..., description="Application ID")
    requisition_id: int = Field(..., description="Requisition ID")
    interview_type: InterviewTypeEnum = Field(..., description="Type of interview")
    start_time: str = Field(..., description="Event start time in ISO format")
    end_time: str = Field(..., description="Event end time in ISO format")


class RescheduleInterviewRequest(BaseModel):
    """Request to reschedule an existing interview."""
    new_start_time: str = Field(..., description="New start time in ISO format")
    new_end_time: str = Field(..., description="New end time in ISO format")


# ============================================================================
# Response Schemas
# ============================================================================

class CalendarSlot(BaseModel):
    """Available calendar time slot."""
    start: str = Field(..., description="Slot start time in ISO format")
    end: str = Field(..., description="Slot end time in ISO format")


class CalendarAvailabilityResponse(BaseModel):
    """Response with available calendar slots."""
    available_slots: List[CalendarSlot] = Field(..., description="List of available time slots")
    interview_type: str = Field(..., description="Type of interview requested")
    total_slots: int = Field(..., description="Total number of available slots")


class InterviewSessionResponse(BaseModel):
    """Response containing created interview session details."""
    id: int = Field(..., description="Interview session ID")
    application_id: int = Field(..., description="Application ID")
    interviewer_id: Optional[int] = Field(None, description="HR manager/Interviewer ID")
    google_event_id: str = Field(..., description="Google Calendar event ID")
    google_meet_link: str = Field(..., description="Google Meet video conference link")
    interview_type: str = Field(..., description="Type of interview")
    calendar_status: str = Field(..., description="Calendar event status")
    scheduled_start_time: str = Field(..., description="Scheduled start time")
    scheduled_end_time: str = Field(..., description="Scheduled end time")
    created_at: str = Field(..., description="Interview session creation timestamp")
    
    class Config:
        from_attributes = True


class ScheduleInterviewResponse(BaseModel):
    """Response after successfully scheduling an interview."""
    message: str = Field(..., description="Success message")
    interview_session: InterviewSessionResponse = Field(..., description="Created interview session")


class RescheduleInterviewResponse(BaseModel):
    """Response after rescheduling an interview."""
    message: str = Field(..., description="Success message")
    interview_session: InterviewSessionResponse = Field(..., description="Updated interview session")


class CancelInterviewResponse(BaseModel):
    """Response after cancelling an interview."""
    message: str = Field(..., description="Success message")
    event_id: str = Field(..., description="Google Calendar event ID that was deleted")


# ============================================================================
# Error Response Schemas (for documentation)
# ============================================================================

class CalendarErrorResponse(BaseModel):
    """Error response from calendar endpoints."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
