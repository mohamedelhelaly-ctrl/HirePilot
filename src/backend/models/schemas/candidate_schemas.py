from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime


class CandidateBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None


class CandidateCreate(CandidateBase):
    lever_id: str


class CandidateUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None


class Candidate(CandidateBase):
    id: int
    lever_id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)