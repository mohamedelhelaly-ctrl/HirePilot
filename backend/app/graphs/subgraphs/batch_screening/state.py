"""
State schema for the batch screening subgraph.

Data flows sequentially through 4 nodes:
    similarity_search → cv_extraction → comparative_scoring → save_results

Each node reads fields from previous nodes and writes its own output fields.
The state is the single source of truth for the entire subgraph run.
"""

from typing import Optional, List, Dict, Set
from pydantic import BaseModel, Field


# ============================================================================
# INTERMEDIATE DATA TYPES
# ============================================================================

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
    source: str          # original CV filename — pipeline key until Node 4

    # ── Candidate identity (used to create the Candidate DB row) ─────────────
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
        description="List of {title: str, company: str, years: float}"
    )
    certifications: List[str] = Field(default_factory=list)
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

    The LLM produces a single overall_score (0–10) for each candidate,
    evaluated comparatively against the full pool. This is normalised
    to combined_score (0–1) for DB storage and display.

    Cosine similarity is NOT part of the final score — it is only used
    as a retrieval filter in Node 1 (top-K selection from ChromaDB).

    recommended_action drives the Application.status update in Node 4:
        "advance"      → SCREENING_PASSED
        "reject"       → SCREENING_REJECTED
        "needs_review" → status unchanged
    """
    source: str                           # original CV filename
    application_id: Optional[int] = None  # set by Node 4 after DB insert

    # LLM-generated overall score (0–10 scale), normalised to 0–1
    llm_score: float
    combined_score: float  # = llm_score / 10.0

    # Single justification covering the overall assessment
    justification: str = ""

    # Supporting detail
    key_strengths: List[str] = Field(default_factory=list)
    key_concerns: List[str] = Field(default_factory=list)

    # Drives Application.status transition
    recommended_action: str = "needs_review"  # "advance" | "reject" | "needs_review"


# ============================================================================
# MAIN SUBGRAPH STATE
# ============================================================================

class BatchScreeningState(BaseModel):
    """
    Shared state for the batch screening subgraph.

    ┌────────────────────┬──────────────────────────────────────────────────┐
    │  INPUT             │ requisition_id                                   │
    ├────────────────────┼──────────────────────────────────────────────────┤
    │  Node 1 output     │ job_description, top_candidates                  │
    │  Node 2 output     │ extracted_cv_data,                               │
    │                    │ existing_candidate_sources,                      │
    │                    │ email_to_candidate_id                            │
    │  Node 3 output     │ comparative_scores                               │
    │  Node 4 output     │ saved_count, updated_count                       │
    ├────────────────────┼──────────────────────────────────────────────────┤
    │  Error tracking    │ error (any node sets this to fail-fast)          │
    └────────────────────┴──────────────────────────────────────────────────┘
    """

    # ── INPUT ──────────────────────────────────────────────────────────────────
    requisition_id: int

    # ── NODE 1 OUTPUT ──────────────────────────────────────────────────────────
    job_description: Optional[str] = None
    top_candidates: List[CandidateDoc] = Field(default_factory=list)

    # ── NODE 2 OUTPUT ──────────────────────────────────────────────────────────
    extracted_cv_data: List[ExtractedCV] = Field(default_factory=list)
    existing_candidate_sources: Set[str] = Field(default_factory=set)
    email_to_candidate_id: Dict[str, int] = Field(default_factory=dict)

    # ── NODE 3 OUTPUT ──────────────────────────────────────────────────────────
    comparative_scores: List[ScoredCandidate] = Field(default_factory=list)

    # ── NODE 4 OUTPUT ──────────────────────────────────────────────────────────
    saved_count: int = 0
    updated_count: int = 0

    # ── ERROR TRACKING ─────────────────────────────────────────────────────────
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True