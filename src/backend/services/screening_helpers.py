"""
Helpers for batch screening readiness checks.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.crud.application_crud import get_screened_applications_for_requisition
from models.crud.interview_session_crud import get_interview_sessions_by_application
from models.crud.requisition_crud import get_requisition_by_id
from models.tables_enums import InterviewStatus


async def requisition_ready_for_interview_rescreen(
    db: AsyncSession,
    requisition_id: int,
) -> bool:
    """
    True when every screened candidate on the requisition has completed at least
    one interview, and there is new interview activity since the last screening
    run (prevents re-triggering until someone interviews again).
    """
    requisition = await get_requisition_by_id(db, requisition_id)
    if not requisition or not requisition.is_active or requisition.screening_in_progress:
        return False

    screened = await get_screened_applications_for_requisition(db, requisition_id)
    if not screened:
        return False

    latest_interview_at: Optional[datetime] = None

    for app in screened:
        sessions = await get_interview_sessions_by_application(db, app.id)
        completed = [
            s for s in sessions
            if getattr(s.status, "value", s.status) == InterviewStatus.COMPLETED.value
        ]
        if not completed:
            return False

        app_interview_at = app.last_interview_completed_at
        if app_interview_at is None:
            end_times = [s.actual_end_time for s in completed if s.actual_end_time]
            if end_times:
                app_interview_at = max(end_times)

        if app_interview_at and (
            latest_interview_at is None or app_interview_at > latest_interview_at
        ):
            latest_interview_at = app_interview_at

    if latest_interview_at is None:
        return False

    if requisition.last_screening_at is None:
        return True

    return latest_interview_at > requisition.last_screening_at
