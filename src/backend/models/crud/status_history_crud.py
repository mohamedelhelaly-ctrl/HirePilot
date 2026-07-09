from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

# from db.models import StatusHistory
# from schemas import StatusHistoryCreate
from models.tables.status_history import StatusHistory
from models.schemas.statusHistory_schemas import StatusHistoryCreate


async def create_status_history(
    db: AsyncSession,
    history: StatusHistoryCreate
) -> StatusHistory:
    """Create a new status history entry."""
    db_history = StatusHistory(**history.model_dump())
    db.add(db_history)
    await db.commit()
    await db.refresh(db_history)
    return db_history


async def get_status_history_by_application(
    db: AsyncSession,
    application_id: int
) -> List[StatusHistory]:
    """Get all status history for an application."""
    result = await db.execute(
        select(StatusHistory)
        .where(StatusHistory.application_id == application_id)
        .order_by(desc(StatusHistory.created_at))
    )
    return list(result.scalars().all())


