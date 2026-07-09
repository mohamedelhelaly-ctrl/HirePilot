from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

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


async def get_candidates_directory(db: AsyncSession) -> List[Dict[str, Any]]:
    """Group all applications by immutable candidate identity for the directory view."""
    result = await db.execute(
        select(Application).options(
            selectinload(Application.candidate),
            selectinload(Application.requisition),
            selectinload(Application.screening_result),
        )
    )
    apps = result.scalars().unique().all()

    grouped: Dict[int, Dict[str, Any]] = {}
    for app in apps:
        if not app.candidate or not app.requisition:
            continue

        candidate_payload = grouped.setdefault(
            app.candidate_id,
            {
                "candidate_id": app.candidate_id,
                "name": app.candidate.full_name,
                "email": app.candidate.email,
                "phone_number": app.candidate.phone,
                "linkedin_url": app.candidate.linkedin_url,
                "applications": [],
            },
        )

        combined = app.combined_score
        screen_score = round(combined * 100) if combined is not None else None

        candidate_payload["applications"].append(
            {
                "application_id": app.id,
                "requisition_id": app.requisition_id,
                "requisition_title": app.requisition.title,
                "department": app.requisition.department,
                "location": app.requisition.location,
                "status": app.status.value if app.status else "unknown",
                "combined_score": combined,
                "screen_score": screen_score,
                "interview_score": app.overall_interview_score,
                "applied_at": app.applied_at,
                "updated_at": app.last_activity_at or app.updated_at,
            }
        )

    candidates: List[Dict[str, Any]] = []
    for payload in grouped.values():
        applications = sorted(
            payload["applications"],
            key=lambda item: (
                item["updated_at"] or item["applied_at"] or datetime.min.replace(tzinfo=timezone.utc),
                item["requisition_title"] or "",
            ),
            reverse=True,
        )
        payload["applications"] = applications
        candidates.append(payload)

    candidates.sort(key=lambda item: (item["name"].lower(), item["candidate_id"]))
    return candidates


