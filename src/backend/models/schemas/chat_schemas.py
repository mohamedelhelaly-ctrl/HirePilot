from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

from models.tables_enums import ChatMessageRole


class ChatThreadCreate(BaseModel):
    requisition_id: int
    title: Optional[str] = "New chat"


class ChatThreadUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)


class ChatThread(BaseModel):
    id: int
    external_id: str
    requisition_id: int
    user_id: Optional[int] = None
    title: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatThreadSummary(ChatThread):
    message_count: int = 0
    last_message_at: Optional[datetime] = None


class ChatMessageCreate(BaseModel):
    thread_id: int
    role: ChatMessageRole
    content: str
    sequence_number: int


class ChatMessage(BaseModel):
    id: int
    thread_id: int
    role: ChatMessageRole
    content: str
    sequence_number: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
