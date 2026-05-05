from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from models.database import get_db
from models.schemas.candidate_schemas import Candidate, CandidateCreate, CandidateUpdate
from models.schemas.application_schemas import Application, ApplicationCreate, ApplicationUpdate
from models.tables_enums import ApplicationStatus
from controllers.CandidateController import CandidateController
from controllers.ApplicationController import ApplicationController

candidate_controller = CandidateController()
application_controller = ApplicationController()
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


@router.post("/applications/", response_model=Application, status_code=status.HTTP_201_CREATED)
async def create_application(
    request: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new application."""
    return await application_controller.create_application(request, db)


@router.get("/by-requisition/{requisition_id}", response_model=List[Candidate])
async def get_candidates_by_requisition(
    requisition_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all candidates for a requisition."""
    return await candidate_controller.get_candidates_by_requisition(requisition_id, db)


@router.get("/applications/{application_id}", response_model=Application)
async def get_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    include_relations: bool = False,
):
    """Get an application by ID."""
    return await application_controller.get_application(application_id, db, include_relations)


@router.patch("/applications/{application_id}", response_model=Application)
async def update_application(
    application_id: int,
    updates: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an application."""
    return await application_controller.update_application(application_id, updates, db)


@router.get("/applications/by-requisition/{requisition_id}", response_model=List[Application])
async def get_applications_by_requisition(
    requisition_id: int,
    db: AsyncSession = Depends(get_db),
    status: Optional[ApplicationStatus] = None,
    min_score: Optional[float] = None,
    skip: int = 0,
    limit: int = 100,
    include_relations: bool = False,
):
    """Get applications for a requisition."""
    return await application_controller.get_applications_by_requisition(
        requisition_id, db, status, min_score, skip, limit, include_relations
    )


@router.patch("/applications/{application_id}/status", response_model=Application)
async def update_application_status(
    application_id: int,
    new_status: ApplicationStatus,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = None,
    reason: Optional[str] = None,
):
    """Update application status."""
    return await application_controller.update_application_status(
        application_id, new_status, db, user_id, reason
    )

