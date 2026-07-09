from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List
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


class CandidateDoc(BaseModel):
    """
    A CV document retrieved from ChromaDB similarity search (Node 1 output).

    cosine_score is a raw distance from ChromaDB (lower = more similar).
    It is used ONLY as a top-K filter in Node 1 — it is never stored in the
    DB or shown to the HR manager. All final scoring is done by the LLM.
    """
    source: str          # original CV filename (ChromaDB metadata key)
    cv_text: str         # raw extracted text of the CV
    cosine_score: float  # raw distance from ChromaDB — internal filter only


class ExtractedCV(BaseModel):
    """
    Structured CV data extracted by the LLM (Node 2 output) OR reconstructed
    from existing ApplicationDetail rows for already-screened candidates.

    is_existing_candidate: True  → Bucket A (already has application on this
                                   requisition; data reconstructed from DB).
                           False → Bucket B (new to this requisition; data
                                   extracted fresh by the LLM).
    """
    source: str

    # ── Candidate identity ─────────────
    full_name: str = ""
    email: str = ""
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None

    skills: List[str] = Field(default_factory=list)
    total_years_experience: float = 0.0
    education: List[dict] = Field(
        default_factory=list,
        description="List of {degree: str, institution: str}"
    )
    previous_roles: List[dict] = Field(
        default_factory=list,
        description=(
            "List of {title, company, start_date, end_date, type} — "
            "start_date/end_date in MM/YYYY or 'Present', "
            "type: full_time | part_time | internship | freelance | volunteer | trainer | instructor"
        )
    )
    certifications: List[str] = Field(default_factory=list)
    projects: List[dict] = Field(
        default_factory=list,
        description="List of project entries with keys such as name, description, technologies, duration"
    )
    summary: str = ""

    # ── Routing flag set by Node 2 ────────────────────────────────────────────
    # True  → Bucket A: update scores only, no re-extraction.
    # False → Bucket B: full insert flow.
    is_existing_candidate: bool = False

    # Debug field — NOT persisted to DB
    raw_llm_output: Optional[str] = None

class ScoredCandidate(BaseModel):
    """
    Scoring result for a single candidate (Node 3 output).

    The LLM produces a single overall_score (0-10) for each candidate,
    evaluated comparatively against the full pool. This is normalised
    to combined_score (0-1) for DB storage and display.

    Cosine similarity is NOT part of the final score — it is only used
    as a retrieval filter in Node 1 (top-K selection from ChromaDB).
    """
    source: str                           # original CV filename
    application_id: Optional[int] = None  # set by Node 4 after DB insert

    # LLM-generated overall score (0–10 scale), normalised to 0–1
    llm_score: float
    combined_score: float  # = llm_score / 10.0

    # Comparative justification covering the overall assessment
    justification: str = ""