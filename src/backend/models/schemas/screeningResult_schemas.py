from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class ScreeningResultBase(BaseModel):
    score: float
    justification: Optional[str] = None


class ScreeningResultCreate(ScreeningResultBase):
    application_id: int


class ScreeningResultUpdate(BaseModel):
    score: Optional[float] = None
    justification: Optional[str] = None
    


class ScreeningResult(ScreeningResultBase):
    id: int
    application_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)