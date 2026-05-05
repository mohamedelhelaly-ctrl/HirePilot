from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from models.database import get_db
from models.schemas.candidate_schemas import Candidate, CandidateCreate, CandidateUpdate
from controllers.CandidateController import CandidateController

candidate_controller = CandidateController()
router = APIRouter()


@router.post("/", response_model=Candidate, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    request: CandidateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new candidate."""
    return await candidate_controller.create_candidate(request, db)


@router.get("/{candidate_id}", response_model=Candidate)
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a candidate by ID."""
    return await candidate_controller.get_candidate(candidate_id, db)


@router.patch("/{candidate_id}", response_model=Candidate)
async def update_candidate(
    candidate_id: int,
    updates: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a candidate."""
    return await candidate_controller.update_candidate(candidate_id, updates, db)


@router.get("/by-requisition/{requisition_id}", response_model=List[Candidate])
async def get_candidates_by_requisition(
    requisition_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all candidates for a requisition."""
    return await candidate_controller.get_candidates_by_requisition(requisition_id, db)

