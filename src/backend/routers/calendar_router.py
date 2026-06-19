"""
Google Calendar API router.
Handles interview scheduling, availability queries, and event management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime

from models.database import get_db
from models.tables.user import User
from models.tables_enums import UserRole, InterviewStatus
from models.schemas.calendar_schemas import (
    CalendarAvailabilityRequest,
    CalendarAvailabilityResponse,
    CalendarSlot,
    ScheduleInterviewRequest,
    ScheduleInterviewResponse,
    RescheduleInterviewRequest,
    RescheduleInterviewResponse,
    CancelInterviewResponse,
    InterviewSessionResponse,
)
from controllers.services.auth_dependencies import get_current_user
from controllers.services.google_calendar_service import (
    get_availability,
    create_interview_event,
    reschedule_event,
    cancel_event,
)
from models.crud import (
    get_application_by_id,
    get_requisition_by_id,
)
from models.crud.interview_session_crud import (
    create_interview_session,
    get_interview_session_by_id,
    update_interview_session_with_google_data,
    delete_interview_session,
)


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/api/calendar",
    tags=["calendar"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing access token"},
        403: {"description": "Forbidden - User not authorized or no Google credentials"},
        404: {"description": "Not Found - Application or requisition not found"},
    }
)


# ============================================================================
# Helper Functions
# ============================================================================

def require_calendar_access(current_user: User) -> User:
    """
    Verify user has permission to access calendar endpoints.
    Only HR_MANAGER and HIRING_MANAGER roles can access calendar features.
    """
    allowed_roles = {UserRole.HR_MANAGER, UserRole.HIRING_MANAGER}
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only HR managers and hiring managers can access calendar features"
        )
    return current_user


# ============================================================================
# Endpoints
# ============================================================================

@router.get(
    "/availability",
    response_model=CalendarAvailabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Available Interview Slots",
    description="Query HR manager's Google Calendar for available time slots"
)
async def get_calendar_availability(
    date_from: str,
    date_to: str,
    interview_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CalendarAvailabilityResponse:
    """
    Query HR manager's Google Calendar for available interview time slots.
    
    Features:
    - Returns time slots excluding weekends
    - Respects working hours (9 AM - 6 PM UTC)
    - Avoids conflicts with existing calendar events
    - Returns slots matching interview duration requirements
    
    Query Parameters:
    - date_from: Start date (ISO format: YYYY-MM-DD)
    - date_to: End date (ISO format: YYYY-MM-DD)
    - interview_type: Type of interview (hr_screen, technical, behavioral, final)
    
    Response:
    - available_slots: List of time slots [{start, end}, ...]
    - interview_type: The requested interview type
    - total_slots: Number of available slots
    
    Interview Durations:
    - hr_screen: 30 minutes
    - technical: 60 minutes
    - behavioral: 45 minutes
    - final: 90 minutes
    
    Requirements:
    - User must have authorized Google Calendar access
    - User role must be HR_MANAGER or HIRING_MANAGER
    
    Raises:
        HTTPException(400): Invalid interview type or date format
        HTTPException(401): User has not connected Google account
        HTTPException(403): User role not authorized for calendar access
        HTTPException(500): Google Calendar API error
    """
    # Verify user has calendar access
    require_calendar_access(current_user)
    
    # Get available slots
    slots = await get_availability(
        db=db,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        interview_type=interview_type
    )
    
    # Convert to CalendarSlot objects
    calendar_slots = [CalendarSlot(start=slot["start"], end=slot["end"]) for slot in slots]
    
    return CalendarAvailabilityResponse(
        available_slots=calendar_slots,
        interview_type=interview_type,
        total_slots=len(calendar_slots)
    )


@router.post(
    "/schedule-interview",
    response_model=ScheduleInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule Interview",
    description="Create Google Calendar event and schedule interview"
)
async def schedule_interview(
    request: ScheduleInterviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ScheduleInterviewResponse:
    """
    Schedule an interview by creating a Google Calendar event with Meet link.
    
    This endpoint:
    1. Validates application and requisition exist
    2. Creates Google Calendar event with Meet conference
    3. Sends invitation emails to candidate and HR manager
    4. Creates InterviewSession record in database
    5. Stores Google Calendar event ID and Meet link
    
    Request Body:
    - candidate_email: Candidate's email address
    - candidate_name: Candidate's full name
    - application_id: ID of the application
    - requisition_id: ID of the requisition
    - interview_type: Type of interview (hr_screen, technical, behavioral, final)
    - start_time: Event start time (ISO 8601 format)
    - end_time: Event end time (ISO 8601 format)
    
    Response:
    - message: Success message
    - interview_session: Created interview session with Google Meet link
    
    Requirements:
    - User must have authorized Google Calendar access
    - Application and requisition must exist
    - Start time must be before end time
    - Duration must match interview type requirements
    
    Raises:
        HTTPException(400): Invalid request data or time range
        HTTPException(401): User has not connected Google account
        HTTPException(403): User role not authorized or application/requisition not found
        HTTPException(409): Application or requisition mismatch
        HTTPException(500): Google Calendar API error or database error
    """
    # Verify user has calendar access
    require_calendar_access(current_user)
    
    # Verify application exists
    application = await get_application_by_id(db, request.application_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {request.application_id} not found"
        )
    
    # Verify requisition exists
    requisition = await get_requisition_by_id(db, request.requisition_id)
    if not requisition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requisition with ID {request.requisition_id} not found"
        )
    
    # Create Google Calendar event
    event_id, meet_link = await create_interview_event(
        db=db,
        user_id=current_user.id,
        candidate_email=request.candidate_email,
        candidate_name=request.candidate_name,
        interview_type=request.interview_type,
        start_time=request.start_time,
        end_time=request.end_time,
        requisition_title=requisition.title,
        hr_manager_name=current_user.full_name,
        hr_manager_email=current_user.email
    )
    
    # Create InterviewSession in database
    # Parse ISO strings to datetime objects for PostgreSQL
    parsed_start_time = datetime.fromisoformat(request.start_time.replace("Z", "+00:00"))
    parsed_end_time = datetime.fromisoformat(request.end_time.replace("Z", "+00:00"))

    interview_session = await create_interview_session(
        db=db,
        application_id=request.application_id,
        interviewer_id=current_user.id,
        interview_type=request.interview_type.value,
        scheduled_start_time=parsed_start_time,
        scheduled_end_time=parsed_end_time,
        google_calendar_event_id=event_id,
        google_meet_link=meet_link,
        calendar_status="confirmed"
    )
    
    # Build response
    session_response = InterviewSessionResponse(
        id=interview_session.id,
        application_id=interview_session.application_id,
        interviewer_id=interview_session.interviewer_id,
        google_event_id=interview_session.google_calendar_event_id,
        google_meet_link=interview_session.google_meet_link,
        interview_type=interview_session.interview_type.value,
        calendar_status=interview_session.status.value if interview_session.status else "confirmed",
        scheduled_start_time=interview_session.scheduled_start_time.isoformat(),
        scheduled_end_time=interview_session.scheduled_end_time.isoformat(),
        created_at=interview_session.created_at.isoformat()
    )
    
    return ScheduleInterviewResponse(
        message="Interview scheduled successfully",
        interview_session=session_response
    )


@router.put(
    "/interviews/{interview_id}/reschedule",
    response_model=RescheduleInterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Reschedule Interview",
    description="Update interview time in Google Calendar"
)
async def reschedule_interview_endpoint(
    interview_id: int,
    request: RescheduleInterviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> RescheduleInterviewResponse:
    """
    Reschedule an existing interview by updating the Google Calendar event.
    
    This endpoint:
    1. Verifies interview session exists
    2. Updates Google Calendar event with new times
    3. Sends "updated" notification to candidate
    4. Updates InterviewSession record in database
    
    Path Parameters:
    - interview_id: ID of the interview session to reschedule
    
    Request Body:
    - new_start_time: New start time (ISO 8601 format)
    - new_end_time: New end time (ISO 8601 format)
    
    Response:
    - message: Success message
    - interview_session: Updated interview session details
    
    Requirements:
    - Interview must exist and belong to current user
    - New times must be valid (start < end)
    - User must have authorized Google Calendar access
    
    Raises:
        HTTPException(401): User has not connected Google account
        HTTPException(403): User not authorized for this interview
        HTTPException(404): Interview session not found
        HTTPException(409): Interview already cancelled
        HTTPException(500): Google Calendar API error or database error
    """
    # Verify user has calendar access
    require_calendar_access(current_user)
    
    # Get interview session
    interview_session = await get_interview_session_by_id(db, interview_id)
    if not interview_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session with ID {interview_id} not found"
        )
    
    # Verify user is the interviewer
    if interview_session.interviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to reschedule this interview"
        )
    
    # Check if interview is already cancelled
    if interview_session.status == InterviewStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot reschedule a cancelled interview"
        )
    
    # Update Google Calendar event
    await reschedule_event(
        db=db,
        user_id=current_user.id,
        google_event_id=interview_session.google_calendar_event_id,
        new_start_time=request.new_start_time,
        new_end_time=request.new_end_time
    )
    
    # Update database
    updated_session = await update_interview_session_with_google_data(
        db=db,
        interview_session_id=interview_id,
        scheduled_start_time=request.new_start_time,
        scheduled_end_time=request.new_end_time,
        calendar_status="confirmed"
    )
    
    # Build response
    session_response = InterviewSessionResponse(
        id=updated_session.id,
        application_id=updated_session.application_id,
        interviewer_id=updated_session.interviewer_id,
        google_event_id=updated_session.google_calendar_event_id,
        google_meet_link=updated_session.google_meet_link,
        interview_type=updated_session.interview_type.value,
        calendar_status=updated_session.status.value if updated_session.status else "confirmed",
        scheduled_start_time=updated_session.scheduled_start_time.isoformat(),
        scheduled_end_time=updated_session.scheduled_end_time.isoformat(),
        created_at=updated_session.created_at.isoformat()
    )
    
    return RescheduleInterviewResponse(
        message="Interview rescheduled successfully",
        interview_session=session_response
    )


@router.delete(
    "/interviews/{interview_id}",
    response_model=CancelInterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Interview",
    description="Delete interview from Google Calendar and mark as cancelled"
)
async def cancel_interview_endpoint(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CancelInterviewResponse:
    """
    Cancel an interview by deleting the Google Calendar event.
    
    This endpoint:
    1. Verifies interview session exists
    2. Deletes Google Calendar event
    3. Sends cancellation notification to candidate
    4. Marks InterviewSession as cancelled in database
    
    Path Parameters:
    - interview_id: ID of the interview session to cancel
    
    Response:
    - message: Success message
    - event_id: Google Calendar event ID that was deleted
    
    Requirements:
    - Interview must exist and belong to current user
    - User must have authorized Google Calendar access
    
    Side Effects:
    - Candidate receives cancellation email from Google Calendar
    - InterviewSession record is marked as cancelled
    
    Raises:
        HTTPException(401): User has not connected Google account
        HTTPException(403): User not authorized for this interview
        HTTPException(404): Interview session not found
        HTTPException(409): Interview already cancelled
        HTTPException(500): Google Calendar API error or database error
    """
    # Verify user has calendar access
    require_calendar_access(current_user)
    
    # Get interview session
    interview_session = await get_interview_session_by_id(db, interview_id)
    if not interview_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session with ID {interview_id} not found"
        )
    
    # Verify user is the interviewer
    if interview_session.interviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to cancel this interview"
        )
    
    # Check if already cancelled
    if interview_session.status == InterviewStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interview is already cancelled"
        )
    
    # Delete from Google Calendar
    await cancel_event(
        db=db,
        user_id=current_user.id,
        google_event_id=interview_session.google_calendar_event_id
    )
    
    # Mark as cancelled in database
    await update_interview_session_with_google_data(
        db=db,
        interview_session_id=interview_id,
        calendar_status="cancelled"
    )
    
    return CancelInterviewResponse(
        message="Interview cancelled successfully",
        event_id=interview_session.google_calendar_event_id
    )
