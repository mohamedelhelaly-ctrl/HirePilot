from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional, List
from datetime import datetime

# from db.models import InterviewSession
# from schemas import InterviewSessionCreate, InterviewSessionUpdate

from models.tables.interview_session import InterviewSession
from models.schemas.interviewSession_schemas import InterviewSessionCreate, InterviewSessionUpdate
from models.tables_enums import InterviewType, InterviewStatus


async def create_interview_session(
    db: AsyncSession,
    application_id: Optional[int] = None,
    interview_type: Optional[str | InterviewType] = None,
    interviewer_id: Optional[int] = None,
    scheduled_start_time: Optional[datetime] = None,
    scheduled_end_time: Optional[datetime] = None,
    google_calendar_event_id: Optional[str] = None,
    google_meet_link: Optional[str] = None,
    calendar_status: Optional[str] = None,
    session: Optional[InterviewSessionCreate] = None
) -> InterviewSession:
    """
    Create a new interview session.
    Pass either a session schema or application_id + interview_type.
    """
    if session:
        db_session = InterviewSession(**session.model_dump())
    elif application_id is not None and interview_type is not None:
        interview_type_enum = (
            InterviewType(interview_type)
            if isinstance(interview_type, str)
            else interview_type
        )
        db_session = InterviewSession(
            application_id=application_id,
            interview_type=interview_type_enum,
            interviewer_id=interviewer_id,
            scheduled_start_time=scheduled_start_time,
            scheduled_end_time=scheduled_end_time,
            google_calendar_event_id=google_calendar_event_id,
            google_meet_link=google_meet_link,
            status=InterviewStatus.SCHEDULED
        )
        if calendar_status:
            # Store calendar_status in summary or another field if available
            # For now, we'll rely on the status field
            pass
    else:
        raise ValueError("Either session or application_id and interview_type must be provided")
    
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    return db_session


async def get_interview_session_by_id(db: AsyncSession, session_id: int) -> Optional[InterviewSession]:
    """Get interview session by ID."""
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_interview_sessions_by_application(
    db: AsyncSession,
    application_id: int
) -> List[InterviewSession]:
    """Get all interview sessions for an application."""
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.application_id == application_id)
        .order_by(InterviewSession.scheduled_start_time)
    )
    return list(result.scalars().all())


async def update_interview_session(
    db: AsyncSession,
    session_id: int,
    session_update: InterviewSessionUpdate
) -> Optional[InterviewSession]:
    """Update interview session."""
    db_session = await get_interview_session_by_id(db, session_id)
    if not db_session:
        return None
    
    update_data = session_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_session, field, value)
    
    await db.commit()
    await db.refresh(db_session)
    return db_session


async def update_interview_session_with_google_data(
    db: AsyncSession,
    interview_session_id: int,
    google_calendar_event_id: Optional[str] = None,
    google_meet_link: Optional[str] = None,
    calendar_status: Optional[str] = None,
    scheduled_start_time: Optional[str] = None,
    scheduled_end_time: Optional[str] = None
) -> Optional[InterviewSession]:
    """
    Update interview session with Google Calendar data.
    Used after creating, rescheduling, or cancelling events.
    """
    db_session = await get_interview_session_by_id(db, interview_session_id)
    if not db_session:
        return None
    
    # Update fields if provided
    if google_calendar_event_id:
        db_session.google_calendar_event_id = google_calendar_event_id
    if google_meet_link:
        db_session.google_meet_link = google_meet_link
    if calendar_status:
        # Map calendar status to our InterviewStatus enum instead of summary
        if calendar_status == "cancelled":
            db_session.status = InterviewStatus.CANCELLED
        elif calendar_status == "confirmed":
            db_session.status = InterviewStatus.SCHEDULED
    if scheduled_start_time:
        db_session.scheduled_start_time = datetime.fromisoformat(
            scheduled_start_time.replace("Z", "+00:00")
        ) if isinstance(scheduled_start_time, str) else scheduled_start_time
    if scheduled_end_time:
        db_session.scheduled_end_time = datetime.fromisoformat(
            scheduled_end_time.replace("Z", "+00:00")
        ) if isinstance(scheduled_end_time, str) else scheduled_end_time
    
    await db.commit()
    await db.refresh(db_session)
    return db_session


async def delete_interview_session(
    db: AsyncSession,
    session_id: int
) -> bool:
    """Delete an interview session (soft delete or hard delete)."""
    db_session = await get_interview_session_by_id(db, session_id)
    if not db_session:
        return False
    
    # Soft delete: mark as cancelled
    db_session.status = InterviewStatus.CANCELLED
    await db.commit()
    return True

