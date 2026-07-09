from pydantic import BaseModel
from typing import Optional, List


class RAGQuery(BaseModel):
    query: str
    requisition_id: Optional[int] = None


class RAGCitation(BaseModel):
    candidate_id: int
    candidate_name: str
    application_id: int
    excerpt: str
    source_type: str  # "cv", "transcript", "assessment"


class RAGResponse(BaseModel):
    answer: str
    citations: List[RAGCitation]