from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime

from ..models import WebhookEvent
from ...schemas import WebhookEventCreate, WebhookEventUpdate


async def create_webhook_event(
    db: AsyncSession,
    event: WebhookEventCreate
) -> WebhookEvent:
    """Create a new webhook event."""
    db_event = WebhookEvent(**event.model_dump())
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


async def get_webhook_event_by_lever_id(
    db: AsyncSession,
    lever_event_id: str
) -> Optional[WebhookEvent]:
    """Get webhook event by Lever event ID (for idempotency)."""
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.lever_event_id == lever_event_id)
    )
    return result.scalar_one_or_none()


async def get_unprocessed_webhook_events(
    db: AsyncSession,
    limit: int = 100
) -> List[WebhookEvent]:
    """Get unprocessed webhook events."""
    result = await db.execute(
        select(WebhookEvent)
        .where(WebhookEvent.processed == False)
        .order_by(WebhookEvent.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_webhook_event(
    db: AsyncSession,
    event_id: int,
    event_update: WebhookEventUpdate
) -> Optional[WebhookEvent]:
    """Update webhook event status."""
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.id == event_id)
    )
    db_event = result.scalar_one_or_none()
    if not db_event:
        return None
    
    update_data = event_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_event, field, value)
    
    await db.commit()
    await db.refresh(db_event)
    return db_event
