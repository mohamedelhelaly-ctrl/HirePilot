from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ..models import Candidate
from ...schemas import CandidateCreate, CandidateUpdate


async def create_candidate(db: AsyncSession, candidate: CandidateCreate) -> Candidate:
    """Create a new candidate."""
    db_candidate = Candidate(**candidate.model_dump())
    db.add(db_candidate)
    await db.commit()
    await db.refresh(db_candidate)
    return db_candidate


async def get_candidate_by_id(db: AsyncSession, candidate_id: int) -> Optional[Candidate]:
    """Get candidate by ID."""
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    return result.scalar_one_or_none()


async def get_candidate_by_lever_id(db: AsyncSession, lever_id: str) -> Optional[Candidate]:
    """Get candidate by Lever ID."""
    result = await db.execute(select(Candidate).where(Candidate.lever_id == lever_id))
    return result.scalar_one_or_none()


async def get_candidate_by_email(db: AsyncSession, email: str) -> Optional[Candidate]:
    """Get candidate by email."""
    result = await db.execute(select(Candidate).where(Candidate.email == email))
    return result.scalar_one_or_none()


async def get_or_create_candidate(db: AsyncSession, candidate: CandidateCreate) -> Candidate:
    """Get existing candidate by lever_id or create new one."""
    db_candidate = await get_candidate_by_lever_id(db, candidate.lever_id)
    if db_candidate:
        return db_candidate
    return await create_candidate(db, candidate)
