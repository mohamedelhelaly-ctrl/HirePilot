from .BaseController import BaseController
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from models.database import get_db
import uuid
from models.schemas import (
    InterviewSessionCreate,
    InterviewSessionUpdate,
    InterviewSession,
    TranscriptChunkCreate
)
from models.crud import(
    create_interview_session,
    get_interview_session_by_id,
    get_interview_sessions_by_application,
    update_interview_session,
    create_transcript_chunk,
    get_transcript_chunks_by_session,
)

class InterviewController(BaseController):
    def __init__(self):
        super().__init__()

    async def create_interview_session(self, session: InterviewSessionCreate, db: AsyncSession) -> InterviewSession:
        return await create_interview_session(db, session=session)
    
    async def get_interview_session_by_id(self, session_id: int, db: AsyncSession) -> InterviewSession:
        session = await get_interview_session_by_id(db, session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
        return session
    
    async def get_interview_sessions_by_application(self, application_id: int, db: AsyncSession) -> list[InterviewSession]:
        return await get_interview_sessions_by_application(db, application_id)
    
    async def update_interview_session(self, session_id: int, session_update: InterviewSessionUpdate, db: AsyncSession) -> InterviewSession:
        updated_session = await update_interview_session(db, session_id, session_update)
        if not updated_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
        return updated_session
    
    async def create_transcript_chunk(self, db: AsyncSession, chunk: TranscriptChunkCreate):
        return await create_transcript_chunk(db, chunk)

    async def get_transcript_chunks_by_session(self, session_id: int, db: AsyncSession):
        return await get_transcript_chunks_by_session(db, session_id)
