from .BaseController import BaseController
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models.schemas.candidate_schemas import (
    Candidate,
    CandidateCreate,
    CandidateUpdate,
)
from models.crud import (
    create_candidate,
    list_candidates,
    get_candidate_by_id,
    get_candidate_by_email,
    get_candidate_by_lever_id,
    get_or_create_candidate,
    get_candidates_by_requisition_id,
)


class CandidateController(BaseController):
    def __init__(self):
        super().__init__()

    async def create_candidate(
        self,
        request: CandidateCreate,
        db: AsyncSession,
    ) -> Candidate:
        try:
            candidate = await create_candidate(db, request)
            return candidate
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create candidate: {exc}"
            )

    async def list_candidates(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Candidate]:
        return await list_candidates(db, skip=skip, limit=limit)

    async def get_candidate(
        self,
        candidate_id: int,
        db: AsyncSession,
    ) -> Candidate:
        candidate = await get_candidate_by_id(db, candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {candidate_id} not found"
            )
        return candidate

    async def update_candidate(
        self,
        candidate_id: int,
        updates: CandidateUpdate,
        db: AsyncSession,
    ) -> Candidate:
        candidate = await get_candidate_by_id(db, candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {candidate_id} not found"
            )

        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(candidate, field, value)

        await db.commit()
        await db.refresh(candidate)
        return candidate

    async def get_candidates_by_requisition(
        self,
        requisition_id: int,
        db: AsyncSession,
    ) -> list[Candidate]:
        return await get_candidates_by_requisition_id(db, requisition_id)