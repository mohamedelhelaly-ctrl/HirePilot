from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List

from db.models import Requisition
from schemas import RequisitionCreate, RequisitionUpdate


async def create_requisition(db: AsyncSession, requisition: RequisitionCreate) -> Requisition:
    """Create a new requisition."""
    db_requisition = Requisition(**requisition.model_dump())
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
    """Reset a specific counter to zero."""
    from datetime import datetime
    
    db_requisition = await get_requisition_by_id(db, requisition_id)
    if not db_requisition:
        return None
    
    if counter_type == "candidate":
        db_requisition.new_candidate_counter = 0
    elif counter_type == "assessment":
        db_requisition.new_assessment_counter = 0
    elif counter_type == "interview":
        db_requisition.new_interview_counter = 0
    
    db_requisition.last_screening_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_requisition)
    return db_requisition
