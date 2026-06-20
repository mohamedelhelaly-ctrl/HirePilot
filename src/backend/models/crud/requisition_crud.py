from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
from datetime import datetime, timezone

# from db.models import Requisition
# from schemas import RequisitionCreate, RequisitionUpdate
from models.tables.requisition import Requisition
from models.schemas.requisition_schemas import RequisitionCreate, RequisitionUpdate
from helpers.config import get_settings


async def create_requisition(db: AsyncSession, requisition: RequisitionCreate) -> Requisition:
    """Create a new requisition."""
    settings = get_settings()
    db_requisition = Requisition(
        **requisition.model_dump(),
        new_candidate_threshold=settings.NEW_CANDIDATE_THRESHOLD,
        new_assessment_threshold=settings.NEW_ASSESSMENT_THRESHOLD,
    )
    db.add(db_requisition)
    await db.commit()
    await db.refresh(db_requisition)
    return db_requisition


async def get_requisition_by_id(db: AsyncSession, requisition_id: int) -> Optional[Requisition]:
    """Get requisition by ID."""
    result = await db.execute(select(Requisition).where(Requisition.id == requisition_id))
    return result.scalar_one_or_none()


async def get_requisition_by_lever_id(db: AsyncSession, lever_id: str) -> Optional[Requisition]:
    """Get requisition by Lever ID."""
    result = await db.execute(select(Requisition).where(Requisition.lever_id == lever_id))
    return result.scalar_one_or_none()


async def get_requisitions(
    db: AsyncSession,
    hiring_manager_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Requisition]:
    """Get requisitions with optional filters."""
    query = select(Requisition)
    
    if hiring_manager_id is not None:
        query = query.where(Requisition.hiring_manager_id == hiring_manager_id)
    if is_active is not None:
        query = query.where(Requisition.is_active == is_active)
    
    query = query.offset(skip).limit(limit).order_by(desc(Requisition.created_at))
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_requisition(
    db: AsyncSession,
    requisition_id: int,
    requisition_update: RequisitionUpdate
) -> Optional[Requisition]:
    """Update requisition information."""
    db_requisition = await get_requisition_by_id(db, requisition_id)
    if not db_requisition:
        return None
    
    update_data = requisition_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_requisition, field, value)
    
    await db.commit()
    await db.refresh(db_requisition)
    return db_requisition


async def increment_requisition_counter(
    db: AsyncSession,
    requisition_id: int,
    counter_type: str  # "candidate", "assessment", "interview"
) -> Optional[Requisition]:
    """Increment a specific counter and return the requisition."""
    db_requisition = await get_requisition_by_id(db, requisition_id)
    if not db_requisition:
        return None
    
    if counter_type == "candidate":
        db_requisition.new_candidate_counter += 1
    elif counter_type == "assessment":
        db_requisition.new_assessment_counter += 1
    elif counter_type == "interview":
        db_requisition.new_interview_counter += 1
    
    await db.commit()
    await db.refresh(db_requisition)
    return db_requisition


async def reset_requisition_counter(
    db: AsyncSession,
    requisition_id: int,
    counter_type: str
) -> Optional[Requisition]:
    """Reset a specific counter to zero and update last_screening_at."""
    db_requisition = await get_requisition_by_id(db, requisition_id)
    if not db_requisition:
        return None
    
    if counter_type == "candidate":
        db_requisition.new_candidate_counter = 0
    elif counter_type == "assessment":
        db_requisition.new_assessment_counter = 0
    elif counter_type == "interview":
        db_requisition.new_interview_counter = 0
    
    db_requisition.last_screening_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_requisition)
    return db_requisition


async def get_requisitions_ready_for_screening(
    db: AsyncSession,
) -> List[Requisition]:
    """
    Return all active requisitions that are ready for automated screening.

    A requisition qualifies when ALL of the following are true:
      - is_active = True
      - screening_in_progress = False   (no concurrent run already running)
      - new_candidate_counter >= new_candidate_threshold

    Called by the scheduler every N minutes to find work to do.
    """
    result = await db.execute(
        select(Requisition).where(
            Requisition.is_active == True,
            Requisition.screening_in_progress == False,
            Requisition.new_candidate_counter >= Requisition.new_candidate_threshold,
        )
    )
    return list(result.scalars().all())


async def get_requisitions_ready_for_interview_rescreen(
    db: AsyncSession,
) -> List[Requisition]:
    """
    Return active requisitions where every screened candidate has completed
    at least one interview and new interview activity exists since last screening.
    """
    from services.screening_helpers import requisition_ready_for_interview_rescreen

    result = await db.execute(
        select(Requisition).where(
            Requisition.is_active == True,
            Requisition.screening_in_progress == False,
        )
    )
    ready: List[Requisition] = []
    for req in result.scalars().all():
        if await requisition_ready_for_interview_rescreen(db, req.id):
            ready.append(req)
    return ready


async def set_screening_in_progress(
    db: AsyncSession,
    requisition_id: int,
    value: bool,
    reset_counter: bool = False,
    counter_type: Optional[str] = None,
) -> Optional[Requisition]:
    """
    Set the screening_in_progress flag on a requisition.

    Args:
        value:         True  â€” mark as running (call before graph invocation)
                       False â€” mark as idle   (call after graph completes/fails)
        reset_counter: When setting value=False, also reset the counter and
                       update last_screening_at. Pass True on successful completion.
        counter_type:  Which counter to reset ("candidate", "interview", "assessment").
                       Defaults to "candidate" for backward compatibility.
    """
    db_requisition = await get_requisition_by_id(db, requisition_id)
    if not db_requisition:
        return None

    db_requisition.screening_in_progress = value

    if not value and reset_counter:
        ctype = counter_type or "candidate"
        if ctype == "candidate":
            db_requisition.new_candidate_counter = 0
        elif ctype == "interview":
            db_requisition.new_interview_counter = 0
        elif ctype == "assessment":
            db_requisition.new_assessment_counter = 0
        db_requisition.last_screening_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_requisition)
    return db_requisition

