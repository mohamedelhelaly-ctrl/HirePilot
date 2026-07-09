from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from models import ApplicationStatus


class StatusHistoryBase(BaseModel):
    from_status: Optional[ApplicationStatus] = None
    to_status: ApplicationStatus
    reason: Optional[str] = None
    notes: Optional[str] = None


class StatusHistoryCreate(StatusHistoryBase):
    application_id: int
    changed_by_user_id: Optional[int] = None


class StatusHistory(StatusHistoryBase):
    id: int
    application_id: int
    changed_by_user_id: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)