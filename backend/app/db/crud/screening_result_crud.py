from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ..models import ScreeningResult
from ...schemas import ScreeningResultCreate, ScreeningResultUpdate


async def create_screening_result(
    db: AsyncSession,
    result: ScreeningResultCreate
) -> ScreeningResult:
    """Create a new screening result."""
    db_result = ScreeningResult(**result.model_dump())
    db.add(db_result)
    await db.commit()
    await db.refresh(db_result)
    return db_result


async def get_screening_result_by_application(
    db: AsyncSession,
    application_id: int
) -> Optional[ScreeningResult]:
    """Get screening result for an application."""
    result = await db.execute(
        select(ScreeningResult).where(ScreeningResult.application_id == application_id)
    )
    return result.scalar_one_or_none()


async def update_screening_result(
    db: AsyncSession,
    application_id: int,
    result_update: ScreeningResultUpdate
) -> Optional[ScreeningResult]:
    """Update screening result."""
    db_result = await get_screening_result_by_application(db, application_id)
    if not db_result:
        return None
    
    update_data = result_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_result, field, value)
    
    await db.commit()
    await db.refresh(db_result)
    return db_result
