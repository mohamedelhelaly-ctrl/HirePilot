from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from .application_schemas import ApplicationWithCandidate


class RequisitionBase(BaseModel):
    title: str
    description: str
    department: Optional[str] = None
    location: Optional[str] = None


class RequisitionCreate(RequisitionBase):
    lever_id: str
    hiring_manager_id: Optional[int] = None


class RequisitionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    hiring_manager_id: Optional[int] = None
    is_active: Optional[bool] = None


class Requisition(RequisitionBase):
    id: int
    lever_id: str
    hiring_manager_id: Optional[int]
    is_active: bool
    new_candidate_counter: int
    new_candidate_threshold: int
    new_assessment_counter: int
    new_assessment_threshold: int
    new_interview_counter: int
    new_interview_threshold: int
    screening_in_progress: bool
    last_screening_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Extended response schemas with relationships
class RequisitionWithApplications(Requisition):
    applications: List[ApplicationWithCandidate] = []


class CreateRequisitionRequest(BaseModel):
    """Request model for creating a requisition."""
    title: str
    description: str
    department: str | None = None
    location: str | None = None
    hiring_manager_id: int | None = None