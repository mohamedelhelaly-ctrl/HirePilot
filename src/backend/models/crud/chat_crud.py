import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.tables.chat_thread import ChatThread
from models.tables.chat_message import ChatMessage
from models.tables_enums import ChatMessageRole
from models.schemas.chat_schemas import ChatThreadCreate


def build_external_thread_id(requisition_id: int) -> str:
    return f"rag-{requisition_id}-{uuid.uuid4()}"


async def create_chat_thread(
    db: AsyncSession,
    data: ChatThreadCreate,
    *,
    external_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> ChatThread:
    thread = ChatThread(
        external_id=external_id or build_external_thread_id(data.requisition_id),
        requisition_id=data.requisition_id,
        user_id=user_id,
        title=data.title or "New chat",
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


async def get_thread_by_external_id(
    db: AsyncSession,
    external_id: str,
) -> Optional[ChatThread]:
    result = await db.execute(
        select(ChatThread).where(ChatThread.external_id == external_id)
    )
    return result.scalar_one_or_none()


async def get_thread_by_id(db: AsyncSession, thread_id: int) -> Optional[ChatThread]:
    result = await db.execute(select(ChatThread).where(ChatThread.id == thread_id))
    return result.scalar_one_or_none()


async def list_threads_by_requisition(
    db: AsyncSession,
    requisition_id: int,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Tuple[ChatThread, int, Optional[datetime]]]:
    msg_count = func.count(ChatMessage.id).label("message_count")
    last_at = func.max(ChatMessage.created_at).label("last_message_at")

    query = (
        select(ChatThread, msg_count, last_at)
        .outerjoin(ChatMessage, ChatMessage.thread_id == ChatThread.id)
        .where(ChatThread.requisition_id == requisition_id)
        .group_by(ChatThread.id)
        .order_by(desc(ChatThread.updated_at))
        .offset(skip)
        .limit(limit)
    )
    if user_id is not None:
        query = query.where(ChatThread.user_id == user_id)

    result = await db.execute(query)
    return list(result.all())


async def append_chat_message(
    db: AsyncSession,
    thread_id: int,
    role: ChatMessageRole,
    content: str,
) -> ChatMessage:
    count_result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.thread_id == thread_id)
    )
    sequence_number = (count_result.scalar() or 0) + 1

    message = ChatMessage(
        thread_id=thread_id,
        role=role,
        content=content,
        sequence_number=sequence_number,
    )
    db.add(message)

    thread = await get_thread_by_id(db, thread_id)
    if thread:
        thread.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(message)
    return message


async def get_messages_by_thread(
    db: AsyncSession,
    thread_id: int,
) -> List[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.sequence_number)
    )
    return list(result.scalars().all())


async def get_message_count(db: AsyncSession, thread_id: int) -> int:
    result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.thread_id == thread_id)
    )
    return result.scalar() or 0


async def update_thread_title(
    db: AsyncSession,
    thread_id: int,
    title: str,
) -> Optional[ChatThread]:
    thread = await get_thread_by_id(db, thread_id)
    if not thread:
        return None
    thread.title = title
    thread.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(thread)
    return thread


async def update_thread_summary(
    db: AsyncSession,
    thread_id: int,
    summary: str,
) -> Optional[ChatThread]:
    thread = await get_thread_by_id(db, thread_id)
    if not thread:
        return None
    thread.summary = summary
    thread.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(thread)
    return thread


async def delete_thread(db: AsyncSession, thread_id: int) -> bool:
    thread = await get_thread_by_id(db, thread_id)
    if not thread:
        return False
    await db.execute(delete(ChatMessage).where(ChatMessage.thread_id == thread_id))
    await db.delete(thread)
    await db.commit()
    return True
