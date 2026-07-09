from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.ChatController import ChatController
from controllers.services.security import decode_access_token
from controllers.services.auth_service import get_current_user as service_get_current_user
from models.database import get_db
from models.schemas.chat_schemas import (
    ChatThread,
    ChatThreadCreate,
    ChatThreadUpdate,
    ChatThreadSummary,
    ChatMessage,
)
from models.tables.user import User

router = APIRouter(prefix="/chat", tags=["chat"])
chat_controller = ChatController()
optional_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None
    try:
        return await service_get_current_user(db, user_id)
    except HTTPException:
        return None


@router.get("/threads", response_model=List[ChatThreadSummary])
async def list_chat_threads(
    requisition_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    user_id = current_user.id if current_user else None
    return await chat_controller.list_threads(db, requisition_id, user_id, skip, limit)


@router.post("/threads", response_model=ChatThread, status_code=status.HTTP_201_CREATED)
async def create_chat_thread(
    body: ChatThreadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    user_id = current_user.id if current_user else None
    return await chat_controller.create_thread(db, body, user_id)


@router.get("/threads/{external_id}/messages", response_model=List[ChatMessage])
async def get_chat_messages(
    external_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    return await chat_controller.get_thread_messages(db, external_id)


@router.patch("/threads/{external_id}", response_model=ChatThread)
async def rename_chat_thread(
    external_id: str,
    body: ChatThreadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    return await chat_controller.rename_thread(db, external_id, body.title)


@router.delete("/threads/{external_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_thread(
    external_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    await chat_controller.delete_thread(db, external_id)
