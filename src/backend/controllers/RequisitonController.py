
from .BaseController import BaseController
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from models.database import get_db
import uuid
from models.schemas import (
    Requisition, 
    RequisitionCreate,
    RequisitionUpdate,
    CreateRequisitionRequest
)
from models.crud import(
    create_requisition,
    get_requisitions,
    get_requisition_by_id,
    update_requisition,
    increment_requisition_counter,
    set_screening_in_progress
)

class RequisitionController(BaseController):
    def __init__(self):
        super().__init__()


    async def create_requisition(self,request: CreateRequisitionRequest, db: AsyncSession):
        # Generate a random lever_id (UUID)
        lever_id = f"lever_{uuid.uuid4().hex[:16]}"

        requisition_data = RequisitionCreate(
            lever_id=lever_id,
            title=request.title,
            description=request.description,
            department=request.department,
            location=request.location,
            hiring_manager_id=None  # Bypassing validation for testing
        )
        # Create requisition in database
        try:
            requisition = await create_requisition(db, requisition_data)
            return requisition
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create requisition: {str(e)}"
            )
        
    
    async def list_requisitions(self, db: AsyncSession,
                                    hiring_manager_id: int | None = None,
                                    is_active: bool | None = None,
                                    skip: int = 0,
                                    limit: int = 100, 
                                ):
        
        requisitions = await get_requisitions(
            db,
            hiring_manager_id=hiring_manager_id,
            is_active=is_active,
            skip=skip,
            limit=limit
        )
        return requisitions
    

    async def get_requisition(self,requisition_id: int, db: AsyncSession,):
        requisition = await get_requisition_by_id(db, requisition_id)
        if not requisition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Requisition with ID {requisition_id} not found"
            )
        return requisition
    

    async def update_requisition(self, requisition_id: int, updates: RequisitionUpdate, db: AsyncSession):
        # Fix invalid hiring_manager_id (0 is not a valid user ID)
        # if updates.hiring_manager_id == 0:
        #     updates.hiring_manager_id = None
        
        requisition = await update_requisition(db, requisition_id, updates)
        if not requisition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Requisition with ID {requisition_id} not found"
            )
        return requisition
    
    
    async def delete_requisition(self, requisition_id: int, db: AsyncSession):
        """Soft delete a requisition by marking it as inactive."""
        requisition = await get_requisition_by_id(db, requisition_id)
        if not requisition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Requisition with ID {requisition_id} not found"
            )
        
        # Mark as inactive
        update_data = RequisitionUpdate(is_active=False)
        await update_requisition(db, requisition_id, update_data)
        return None
    
    async def increment_requisition_counter(self, db: AsyncSession, requisition_id: int, counter_type: str):
        return await increment_requisition_counter(
            db, requisition_id, counter_type
        )
    
    async def set_screening_in_progress(self, db: AsyncSession, requisition_id: int, value: bool, reset_counter: bool = False):
        return await set_screening_in_progress(db, requisition_id, value, reset_counter)
    