from .BaseController import BaseController
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List, Optional

from models.schemas.application_schemas import (
    Application,
    ApplicationCreate,
    ApplicationUpdate,
)

from models.crud import(
    #application_crud
    create_application,
    get_application_by_id,
    get_applications_by_requisition,
    update_application,
    update_application_status,
    get_application_by_lever_opportunity_id,

    #application_detail_crud
    get_application_details,
    create_application_detail,
    create_application_details_bulk,
    
    #screening_result_crud
    get_screening_result_by_application,
    create_screening_result,
    update_screening_result
)


from models.schemas.applicationDetail_schemas import (
    ApplicationDetail,
    ApplicationDetailCreate
)

from models.tables_enums import ApplicationStatus

from models.schemas.screeningResult_schemas import(
    ScreeningResult,
    ScreeningResultUpdate,
    ScreeningResultCreate
)


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
    
    async def get_application_by_lever_opportunity_id(
        self,
        db: AsyncSession,
        lever_opportunity_id: str
    ) -> Optional[Application]:
        return await get_application_by_lever_opportunity_id(db, lever_opportunity_id)
    

    ########## Application Details Methods ##########
    async def get_application_details(
            self,
            db: AsyncSession,
            application_id: int
        ) -> List[ApplicationDetail]:
        return await get_application_details(db, application_id)
    
    async def create_application_detail(
            self,
            db: AsyncSession,
            detail: ApplicationDetailCreate
    ) -> ApplicationDetail:
        return await create_application_detail(db, detail)
    
    async def create_many_application_details(
            self,
            db: AsyncSession,
            details: List[ApplicationDetailCreate]
    ) -> List[ApplicationDetail]:
        return await create_application_details_bulk(db, details)
    

    ########### Screening Result Methods ###########

    async def get_screening_result_by_applicationId(
        self,
        db: AsyncSession,
        application_id: int
    ) -> Optional[ScreeningResult]:
        return await get_screening_result_by_application(db, application_id)
    
    async def update_screening_result(
        self,
        db: AsyncSession,
        application_id: int,
        result_update: ScreeningResultUpdate
    ) -> Optional[ScreeningResult]:
        return await update_screening_result(db, application_id, result_update)
    
    async def create_screening_result(
            self,
            db: AsyncSession,
            screening_result: ScreeningResultCreate
    ) -> Optional[ScreeningResult]:
        return await create_screening_result(db, screening_result)
    
