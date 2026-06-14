from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CandidateDirectoryApplication(BaseModel):
    application_id: int
    requisition_id: int
    requisition_title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    status: str
    combined_score: Optional[float] = None
    screen_score: Optional[int] = None
    interview_score: Optional[float] = None
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CandidateDirectoryItem(BaseModel):
    candidate_id: int
    name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    linkedin_url: Optional[str] = None
    applications: List[CandidateDirectoryApplication] = []

    model_config = ConfigDict(from_attributes=True)


class CandidatesDirectoryResponse(BaseModel):
    success: bool = True
    candidates: List[CandidateDirectoryItem]
    count: int
