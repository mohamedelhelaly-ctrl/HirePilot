from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from db.models import ApplicationDetail
from schemas import ApplicationDetailCreate


async def create_application_detail(
    db: AsyncSession,
    detail: ApplicationDetailCreate
) -> ApplicationDetail:
    """Create a new application detail."""
    db_detail = ApplicationDetail(**detail.model_dump())
    db.add(db_detail)
    await db.commit()
    await db.refresh(db_detail)
    return db_detail


async def create_application_details_bulk(
    db: AsyncSession,
    details: List[ApplicationDetailCreate]
) -> List[ApplicationDetail]:
    """Create multiple application details in bulk."""
    db_details = [ApplicationDetail(**detail.model_dump()) for detail in details]
    db.add_all(db_details)
    await db.commit()
    return db_details


async def get_application_details(
    db: AsyncSession,
    application_id: int
) -> List[ApplicationDetail]:
    """Get all details for an application."""
    result = await db.execute(
        select(ApplicationDetail).where(ApplicationDetail.application_id == application_id)
    )
    return list(result.scalars().all())


