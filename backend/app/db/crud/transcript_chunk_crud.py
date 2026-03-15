from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..models import TranscriptChunk
from ...schemas import TranscriptChunkCreate


async def create_transcript_chunk(
    db: AsyncSession,
    chunk: TranscriptChunkCreate
) -> TranscriptChunk:
    """Create a new transcript chunk."""
    db_chunk = TranscriptChunk(**chunk.model_dump())
    db.add(db_chunk)
    await db.commit()
    await db.refresh(db_chunk)
    return db_chunk


async def get_transcript_chunks_by_session(
    db: AsyncSession,
    session_id: int
) -> List[TranscriptChunk]:
    """Get all transcript chunks for a session, ordered by sequence."""
    result = await db.execute(
        select(TranscriptChunk)
        .where(TranscriptChunk.session_id == session_id)
        .order_by(TranscriptChunk.sequence_number)
    )
    return list(result.scalars().all())
