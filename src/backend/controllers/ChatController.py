from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .BaseController import BaseController
from models.schemas.chat_schemas import (
    ChatThread,
    ChatThreadCreate,
    ChatThreadSummary,
    ChatMessage,
)
from models.crud.chat_crud import (
    create_chat_thread,
    get_thread_by_external_id,
    get_thread_by_id,
    list_threads_by_requisition,
    get_messages_by_thread,
    get_message_count,
    update_thread_title,
    delete_thread,
)


def _auto_title_from_message(text: str, max_len: int = 80) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "New chat"
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


class ChatController(BaseController):
    def __init__(self):
        super().__init__()

    async def create_thread(
        self,
        db: AsyncSession,
        data: ChatThreadCreate,
        user_id: Optional[int] = None,
    ) -> ChatThread:
        thread = await create_chat_thread(db, data, user_id=user_id)
        return ChatThread.model_validate(thread)

    async def list_threads(
        self,
        db: AsyncSession,
        requisition_id: int,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ChatThreadSummary]:
        rows = await list_threads_by_requisition(
            db, requisition_id, user_id, skip, limit
        )
        results: List[ChatThreadSummary] = []
        for thread, message_count, last_message_at in rows:
            base = ChatThread.model_validate(thread)
            results.append(
                ChatThreadSummary(
                    **base.model_dump(),
                    message_count=message_count or 0,
                    last_message_at=last_message_at,
                )
            )
        return results

    async def get_thread(
        self,
        db: AsyncSession,
        external_id: str,
    ) -> ChatThread:
        thread = await get_thread_by_external_id(db, external_id)
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat thread '{external_id}' not found",
            )
        return ChatThread.model_validate(thread)

    async def get_thread_messages(
        self,
        db: AsyncSession,
        external_id: str,
    ) -> List[ChatMessage]:
        thread = await get_thread_by_external_id(db, external_id)
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat thread '{external_id}' not found",
            )
        messages = await get_messages_by_thread(db, thread.id)
        return [ChatMessage.model_validate(m) for m in messages]

    async def rename_thread(
        self,
        db: AsyncSession,
        external_id: str,
        title: str,
    ) -> ChatThread:
        thread = await get_thread_by_external_id(db, external_id)
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat thread '{external_id}' not found",
            )
        updated = await update_thread_title(db, thread.id, title)
        return ChatThread.model_validate(updated)

    async def delete_thread(self, db: AsyncSession, external_id: str) -> None:
        thread = await get_thread_by_external_id(db, external_id)
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat thread '{external_id}' not found",
            )
        await delete_thread(db, thread.id)

    async def ensure_thread_for_rag(
        self,
        db: AsyncSession,
        external_id: Optional[str],
        requisition_id: int,
        user_id: Optional[int] = None,
    ) -> ChatThread:
        if external_id:
            thread = await get_thread_by_external_id(db, external_id)
            if thread:
                if thread.requisition_id != requisition_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Chat thread does not belong to this requisition",
                    )
                return ChatThread.model_validate(thread)

        created = await create_chat_thread(
            db,
            ChatThreadCreate(requisition_id=requisition_id),
            user_id=user_id,
        )
        return ChatThread.model_validate(created)

    async def set_title_from_first_message(
        self,
        db: AsyncSession,
        thread_id: int,
        user_text: str,
    ) -> None:
        count = await get_message_count(db, thread_id)
        if count == 0:
            thread = await get_thread_by_id(db, thread_id)
            if thread and thread.title == "New chat":
                await update_thread_title(
                    db, thread_id, _auto_title_from_message(user_text)
                )
