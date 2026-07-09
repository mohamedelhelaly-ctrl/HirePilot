from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class TranscriptChunkBase(BaseModel):
    text: str
    speaker: Optional[str] = None
    sequence_number: int
    offset_seconds: Optional[float] = None


class TranscriptChunkCreate(TranscriptChunkBase):
    session_id: int


class TranscriptChunk(TranscriptChunkBase):
    id: int
    session_id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)