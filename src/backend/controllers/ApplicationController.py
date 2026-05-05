from .BaseController import BaseController
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List, Optional

from models.schemas.application_schemas import (
    Application,
    ApplicationCreate,
    ApplicationUpdate,
)
from models.crud.application_crud import (
    create_application,
    get_application_by_id,
    get_applications_by_requisition,
    update_application,
    update_application_status,
)
from models.tables_enums import ApplicationStatus


class ApplicationController(BaseController):
    def __init__(self):
        super().__init__()

    async def create_application(
        self,
        request: ApplicationCreate,
        db: AsyncSession,
    ) -> Application:
        try:
            application = await create_application(db, request)
            return application
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create application: {exc}"
            )

    async def get_application(
        self,
        application_id: int,
        db: AsyncSession,
        include_relations: bool = False,
    ) -> Application:
        application = await get_application_by_id(db, application_id, include_relations)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID {application_id} not found"
            )
        return application

    async def update_application(
        self,
        application_id: int,
        updates: ApplicationUpdate,
        db: AsyncSession,
    ) -> Application:
        application = await update_application(db, application_id, updates)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID {application_id} not found"
            )
        return application

    async def get_applications_by_requisition(
        self,
        requisition_id: int,
        db: AsyncSession,
        status: Optional[ApplicationStatus] = None,
        min_score: Optional[float] = None,
        skip: int = 0,
        limit: int = 100,
        include_relations: bool = False,
    ) -> List[Application]:
        return await get_applications_by_requisition(
            db, requisition_id, status, min_score, skip, limit, include_relations
        )

    async def update_application_status(
        self,
        application_id: int,
        new_status: ApplicationStatus,
        db: AsyncSession,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Application:
        application = await update_application_status(db, application_id, new_status, user_id, reason)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID {application_id} not found"
            )
        return application