"""
Google Calendar Service module.
Handles calendar availability queries and interview event scheduling with Google Meet.

Uses Google Calendar API v3 (https://developers.google.com/calendar/api/guides/overview)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from zoneinfo import ZoneInfo

from helpers.config import get_settings
from controllers.services.google_oauth_service import get_valid_google_access_token

# ============================================================================
# Configuration
# ============================================================================

settings = get_settings()
GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

# Interview type to duration mapping (in minutes)
INTERVIEW_DURATIONS = {
    "hr_screen": 30,
    "technical": 60,
    "behavioral": 45,
    "final": 90,
}

# Working hours (9 AM to 6 PM)
WORK_DAY_START_HOUR = 9
WORK_DAY_END_HOUR = 18

# Minimum time buffer between events (minutes)
MIN_BUFFER_MINUTES = 15


# ============================================================================
# Calendar Event Operations
# ============================================================================

async def get_availability(
    db: AsyncSession,
    user_id: int,
    date_from: str,  # ISO format: "2026-06-20"
    date_to: str,
    interview_type: str
) -> List[Dict[str, str]]:
    """
    Query HR manager's Google Calendar and return available interview time slots.
    
    Features:
    - Excludes weekends (Saturday, Sunday)
    - Respects working hours (9 AM - 6 PM)
    - Avoids conflicts with existing events
    - Returns slots matching interview duration
    - Timezone-aware calculations
    
    Args:
        db: Database session
        user_id: HR manager's user ID
        date_from: Start date in ISO format (inclusive)
        date_to: End date in ISO format (inclusive)
        interview_type: Type of interview (hr_screen, technical, behavioral, final)
        
    Returns:
        List of available time slots:
        [
            {"start": "2026-06-20T10:00:00Z", "end": "2026-06-20T10:30:00Z"},
            {"start": "2026-06-20T10:45:00Z", "end": "2026-06-20T11:15:00Z"},
            ...
        ]
        
    Raises:
        HTTPException: If user has no Google credentials or API call fails
    """
    # Validate interview type
    if interview_type not in INTERVIEW_DURATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid interview type. Allowed: {list(INTERVIEW_DURATIONS.keys())}"
        )
    
    interview_duration = INTERVIEW_DURATIONS[interview_type]
    
    # Get valid access token
    access_token = await get_valid_google_access_token(db, user_id)
    
    # Query busy times from Google Calendar
    busy_times = await _get_busy_times(
        access_token=access_token,
        date_from=date_from,
        date_to=date_to
    )
    
    # Generate available slots
    available_slots = _generate_available_slots(
        date_from=date_from,
        date_to=date_to,
        busy_times=busy_times,
        duration_minutes=interview_duration
    )
    
    return available_slots


async def _get_busy_times(
    access_token: str,
    date_from: str,
    date_to: str
) -> List[Dict[str, str]]:
    """
    Query Google Calendar for busy times in the given date range.
    
    Uses Calendar API freebusy endpoint to find occupied time slots.
    
    Args:
        access_token: Google OAuth access token
        date_from: Start date (ISO format)
        date_to: End date (ISO format)
        
    Returns:
        List of busy time periods:
        [
            {"start": "2026-06-20T10:00:00Z", "end": "2026-06-20T11:00:00Z"},
            ...
        ]
    """
    # Convert dates to RFC3339 format with time
    time_from = f"{date_from}T00:00:00Z"
    time_to = f"{date_to}T23:59:59Z"
    
    # Get the primary calendar ID (usually "primary")
    calendar_id = "primary"
    
    # Build freebusy query
    url = f"{GOOGLE_CALENDAR_API_BASE}/freeBusy"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "timeMin": time_from,
        "timeMax": time_to,
        "items": [{"id": calendar_id}]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            busy_periods = result.get("calendars", {}).get(calendar_id, {}).get("busy", [])
            return busy_periods
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query Google Calendar: {str(e)}"
        )


def _generate_available_slots(
    date_from: str,
    date_to: str,
    busy_times: List[Dict[str, str]],
    duration_minutes: int
) -> List[Dict[str, str]]:
    """
    Generate list of available time slots from busy times.
    
    Args:
        date_from: Start date (ISO format)
        date_to: End date (ISO format)
        busy_times: List of busy time periods
        duration_minutes: Required slot duration
        
    Returns:
        List of available slots in ISO format
    """
    slots = []
    
    # Parse dates
    current_date = datetime.fromisoformat(date_from).date()
    end_date = datetime.fromisoformat(date_to).date()
    
    # Iterate through each day
    while current_date <= end_date:
        # Skip weekends (Friday and Saturday)
        if current_date.weekday() in (4, 5):  # 4=Friday, 5=Saturday
            current_date += timedelta(days=1)
            continue
        
        # Generate slots for this day
        day_slots = _generate_day_slots(
            date=current_date,
            busy_times=busy_times,
            duration_minutes=duration_minutes
        )
        slots.extend(day_slots)
        
        current_date += timedelta(days=1)
    
    return slots


def _generate_day_slots(
    date: Any,  # datetime.date
    busy_times: List[Dict[str, str]],
    duration_minutes: int
) -> List[Dict[str, str]]:
    """
    Generate available slots for a single day.
    
    Args:
        date: The date to generate slots for
        busy_times: List of busy periods (covers entire date range)
        duration_minutes: Required duration
        
    Returns:
        List of available slots for the day
    """
    slots = []
    # Get local timezone
    local_tz = datetime.now().astimezone().tzinfo
    
    # Working hours for this day (in local timezone)
    work_start = datetime.combine(date, datetime.min.time()).replace(hour=WORK_DAY_START_HOUR, tzinfo=local_tz)
    work_end = datetime.combine(date, datetime.min.time()).replace(hour=WORK_DAY_END_HOUR, tzinfo=local_tz)
    
    # Check each potential time slot
    current_time = work_start
    slot_duration = timedelta(minutes=duration_minutes)
    
    while current_time + slot_duration <= work_end:
        slot_end = current_time + slot_duration
        
        # Check if this slot conflicts with any busy time
        is_available = True
        for busy in busy_times:
            busy_start = datetime.fromisoformat(busy["start"].replace("Z", "+00:00"))
            busy_end = datetime.fromisoformat(busy["end"].replace("Z", "+00:00"))
            
            # current_time and slot_end are aware, busy_start and busy_end are aware
            if current_time < busy_end and slot_end > busy_start:
                is_available = False
                break
        
        if is_available:
            slots.append({
                "start": current_time.isoformat(),
                "end": slot_end.isoformat()
            })
        
        # Move to next slot (with buffer)
        current_time += timedelta(minutes=duration_minutes + MIN_BUFFER_MINUTES)
    
    return slots


async def create_interview_event(
    db: AsyncSession,
    user_id: int,
    candidate_email: str,
    candidate_name: str,
    interview_type: str,
    start_time: str,  # ISO format
    end_time: str,
    requisition_title: str,
    hr_manager_name: str,
    hr_manager_email: Optional[str] = None
) -> tuple:
    """
    Create a Google Calendar event with Meet link for interview.
    
    Features:
    - Creates calendar event with Meet conference
    - Invites candidate and HR manager
    - Includes requisition details in description
    - Returns event ID and Meet link
    
    Args:
        db: Database session
        user_id: HR manager's user ID
        candidate_email: Candidate's email
        candidate_name: Candidate's full name
        interview_type: Type of interview
        start_time: Event start time (ISO format)
        end_time: Event end time (ISO format)
        requisition_title: Job title from requisition
        hr_manager_name: HR manager's name
        hr_manager_email: HR manager's email (optional, defaults to primary account)
        
    Returns:
        Tuple of (google_event_id, google_meet_link)
        
    Raises:
        HTTPException: If event creation fails
    """
    # Get access token
    access_token = await get_valid_google_access_token(db, user_id)
    
    # Build event object
    event = {
        "summary": f"{requisition_title} - {interview_type.title()} Interview - {candidate_name}",
        "description": f"""
Candidate: {candidate_name} ({candidate_email})
Interview Type: {interview_type.title()}
Position: {requisition_title}
Interviewer: {hr_manager_name}

Join using the Meet link below. The candidate will receive a calendar invitation.
""",
        "start": {
            "dateTime": start_time,
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "UTC"
        },
        "attendees": [
            {"email": candidate_email, "displayName": candidate_name},
        ],
        "conferenceData": {
            "createRequest": {
                "requestId": f"interview-{user_id}-{int(datetime.utcnow().timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"}
            }
        },
        "reminders": {
            "useDefault": True
        }
    }
    
    # Add HR manager to attendees if email provided
    if hr_manager_email:
        event["attendees"].append({
            "email": hr_manager_email,
            "displayName": hr_manager_name,
            "organizer": True
        })
    
    # Create event via Calendar API
    url = f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"conferenceDataVersion": 1, "sendNotifications": True}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=event,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            result = response.json()
            event_id = result.get("id")
            meet_link = result.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri", "")
            
            if not event_id or not meet_link:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create Meet link"
                )
            
            return (event_id, meet_link)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Google Calendar event: {str(e)}"
        )


async def reschedule_event(
    db: AsyncSession,
    user_id: int,
    google_event_id: str,
    new_start_time: str,
    new_end_time: str
) -> Dict[str, Any]:
    """
    Update a Google Calendar event with new times.
    
    Args:
        db: Database session
        user_id: HR manager's user ID
        google_event_id: Google Calendar event ID
        new_start_time: New start time (ISO format)
        new_end_time: New end time (ISO format)
        
    Returns:
        Updated event details
        
    Raises:
        HTTPException: If reschedule fails
    """
    # Get access token
    access_token = await get_valid_google_access_token(db, user_id)
    
    # Get existing event
    url = f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events/{google_event_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Get current event
            get_response = await client.get(url, headers=headers)
            get_response.raise_for_status()
            event = get_response.json()
            
            # Update times
            event["start"]["dateTime"] = new_start_time
            event["end"]["dateTime"] = new_end_time
            
            # Update event
            put_response = await client.put(
                url,
                json=event,
                headers=headers,
                params={"sendNotifications": True}
            )
            put_response.raise_for_status()
            
            return put_response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reschedule Google Calendar event: {str(e)}"
        )


async def cancel_event(
    db: AsyncSession,
    user_id: int,
    google_event_id: str
) -> Dict[str, str]:
    """
    Delete a Google Calendar event.
    
    Args:
        db: Database session
        user_id: HR manager's user ID
        google_event_id: Google Calendar event ID
        
    Returns:
        Confirmation dict
        
    Raises:
        HTTPException: If deletion fails
    """
    # Get access token
    access_token = await get_valid_google_access_token(db, user_id)
    
    # Delete event
    url = f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events/{google_event_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers=headers,
                params={"sendNotifications": True}
            )
            response.raise_for_status()
            
            return {"message": "Event deleted successfully", "event_id": google_event_id}
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete Google Calendar event: {str(e)}"
        )
