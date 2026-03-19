from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from db.models import InterviewSession
from schemas import InterviewSessionCreate, InterviewSessionUpdate


async def create_interview_session(
    db: AsyncSession,
    session: InterviewSessionCreate
) -> InterviewSession:
    """Create a new interview session."""
    db_session = InterviewSession(**session.model_dump())
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


