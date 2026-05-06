from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import sys
from pathlib import Path
from fastapi.responses import JSONResponse as JsonResponse
import logging
logger = logging.getLogger('uvicorn.error')

# Add app directory to path for imports
# sys.path.insert(0, str(Path(__file__)))


from models.database import get_db

from models.schemas import (
    Requisition, 
    RequisitionUpdate,
    CreateRequisitionRequest
)

from controllers.RequisitonController import RequisitionController
req_controller = RequisitionController()

router = APIRouter()


@router.post("/", response_model=Requisition, status_code=status.HTTP_201_CREATED)
async def create_requisition(
    request: CreateRequisitionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new requisition.
    
    Auto-generates:
    - lever_id: Random UUID string
    
    Required fields:
    - title: Job title
    - description: Job description
    
    Optional fields:
    - department: Department name
    - location: Job location
    - hiring_manager_id: ID of the assigned hiring manager
    """
    return await req_controller.create_requisition(request, db)
    


@router.get("/", response_model=List[Requisition])
async def list_requisitions(
    db: AsyncSession = Depends(get_db),
    hiring_manager_id: int | None = None,
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """
    List all requisitions with optional filters.
    
    Query parameters:
    - hiring_manager_id: Filter by hiring manager
    - is_active: Filter by active status
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    """
    return await req_controller.list_requisitions(
        hiring_manager_id=hiring_manager_id,
        is_active=is_active,
        skip=skip,
        limit=limit,
        db=db
    )


@router.get("/{requisition_id}", response_model=Requisition)
async def get_requisition(
    requisition_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a requisition by ID."""
    return await req_controller.get_requisition(requisition_id,db)



@router.patch("/{requisition_id}", response_model=Requisition)
async def update_requisition(
    requisition_id: int,
    updates: RequisitionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a requisition."""
    return await req_controller.update_requisition(requisition_id, updates, db)


@router.delete("/{requisition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requisition(
    requisition_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a requisition by marking it as inactive."""
    await req_controller.delete_requisition(requisition_id, db)
    return JsonResponse(status_code=status.HTTP_200_OK, content={
        "message": f"Requisition with ID {requisition_id} has been marked as inactive."
    })