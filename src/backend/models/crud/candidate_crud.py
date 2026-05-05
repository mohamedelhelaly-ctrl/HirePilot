from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional


# from db.models import Candidate
# from schemas import CandidateCreate, CandidateUpdate
from models.tables.candidate import Candidate
from models.tables.application import Application
from models.schemas.candidate_schemas import CandidateCreate, CandidateUpdate, Candidate as CandidateSchema


async def create_candidate(db: AsyncSession, candidate: CandidateCreate) -> CandidateSchema:
    """Create a new candidate."""
    db_candidate = Candidate(**candidate.model_dump())
    db.add(db_candidate)
    await db.commit()
    await db.refresh(db_candidate)
    return db_candidate


async def get_candidate_by_id(db: AsyncSession, candidate_id: int) -> Optional[CandidateSchema]:
    """Get candidate by ID."""
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    return result.scalar_one_or_none()


async def get_candidate_by_lever_id(db: AsyncSession, lever_id: str) -> Optional[CandidateSchema]:
    """Get candidate by Lever ID."""
    result = await db.execute(select(Candidate).where(Candidate.lever_id == lever_id))
    return result.scalar_one_or_none()


async def get_candidate_by_email(db: AsyncSession, email: str) -> Optional[CandidateSchema]:
    """Get candidate by email."""
    result = await db.execute(select(Candidate).where(Candidate.email == email))
    return result.scalar_one_or_none()


async def get_or_create_candidate(db: AsyncSession, candidate: CandidateCreate) -> CandidateSchema:
    """Get existing candidate by lever_id or create new one."""
    db_candidate = await get_candidate_by_lever_id(db, candidate.lever_id)
    if db_candidate:
        return db_candidate
    return await create_candidate(db, candidate)


async def list_candidates(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[CandidateSchema]:
    """Get a paginated list of candidates."""
    result = await db.execute(
        select(Candidate).offset(skip).limit(limit)
    )
    rows = result.scalars().all()
    return rows


async def get_candidates_by_requisition_id(
    db: AsyncSession,
    requisition_id: int
) -> List[CandidateSchema]:
    """Get all candidates that have an application for the given requisition."""
    subquery = select(Application.candidate_id).where(
        Application.requisition_id == requisition_id
    )
    result = await db.execute(
        select(Candidate).where(Candidate.id.in_(subquery))
    )
    return result.scalars().all()


