from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime


class ApplicationDetailBase(BaseModel):
    key: str
    value: Any
    relevance: Optional[str] = None


class ApplicationDetailCreate(ApplicationDetailBase):
    application_id: int


class ApplicationDetail(ApplicationDetailBase):
    id: int
    application_id: int
    extracted_at: datetime
    
    model_config = ConfigDict(from_attributes=True)