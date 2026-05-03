from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List
from datetime import datetime

# from db.models import Application, ApplicationStatus
# from schemas import ApplicationCreate, ApplicationUpdate
# from schemas import StatusHistoryCreate

from models.tables.application import Application
from models.tables_enums import ApplicationStatus
from models.schemas.application_schemas import ApplicationCreate, ApplicationUpdate
from models.schemas.statusHistory_schemas import StatusHistoryCreate


async def create_application(db: AsyncSession, application: ApplicationCreate) -> Application:
    """Create a new application."""
    db_application = Application(**application.model_dump())
    db.add(db_application)
    await db.commit()
    await db.refresh(db_application)
    return db_application


async def get_application_by_id(
    db: AsyncSession,
    application_id: int,
    include_relations: bool = False
) -> Optional[Application]:
    """Get application by ID, optionally with related data."""
    query = select(Application).where(Application.id == application_id)
    
    if include_relations:
        query = query.options(
            joinedload(Application.candidate),
            joinedload(Application.screening_result),
            selectinload(Application.interview_sessions),
            selectinload(Application.details)
        )
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_application_by_lever_opportunity_id(
    db: AsyncSession,
    lever_opportunity_id: str
) -> Optional[Application]:
    """Get application by Lever opportunity ID."""
    result = await db.execute(
        select(Application).where(Application.lever_opportunity_id == lever_opportunity_id)
    )
    return result.scalar_one_or_none()


async def get_applications_by_requisition(
    db: AsyncSession,
    requisition_id: int,
    status: Optional[ApplicationStatus] = None,
    min_score: Optional[float] = None,
    skip: int = 0,
    limit: int = 100,
    include_relations: bool = False
) -> List[Application]:
    """Get applications for a requisition with optional filters, ordered by combined score."""
    query = select(Application).where(Application.requisition_id == requisition_id)
    
    if status:
        query = query.where(Application.status == status)
    if min_score is not None:
        query = query.where(Application.combined_score >= min_score)
    
    if include_relations:
        query = query.options(
            joinedload(Application.candidate),
            joinedload(Application.screening_result)
        )
    
    query = query.order_by(desc(Application.combined_score)).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_application(
    db: AsyncSession,
    application_id: int,
    application_update: ApplicationUpdate
) -> Optional[Application]:
    """Update application information."""
    db_application = await get_application_by_id(db, application_id)
    if not db_application:
        return None
    
    update_data = application_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_application, field, value)
    
    db_application.last_activity_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_application)
    return db_application


async def update_application_status(
    db: AsyncSession,
    application_id: int,
    new_status: ApplicationStatus,
    user_id: Optional[int] = None,
    reason: Optional[str] = None
) -> Optional[Application]:
    """Update application status and create status history entry."""
    from . import status_history_crud
    
    db_application = await get_application_by_id(db, application_id)
    if not db_application:
        return None
    
    old_status = db_application.status
    db_application.status = new_status
    db_application.last_activity_at = datetime.utcnow()
    

    
    history_entry = StatusHistoryCreate(
        application_id=application_id,
        from_status=old_status,
        to_status=new_status,
        changed_by_user_id=user_id,
        reason=reason
    )
    await status_history_crud.create_status_history(db, history_entry)
    
    await db.commit()
    await db.refresh(db_application)
    return db_application
