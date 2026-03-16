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

    Carries the raw CV text and its cosine distance score from ChromaDB.
    The cosine_score is a *distance* (lower = more similar) for LangChain's
    default Chroma backend, normalised to a similarity in Node 3.

    Candidates are identified by *source* (the original filename stored as
    ChromaDB metadata) throughout Nodes 1–3.  The real application_id is
    only available after Node 4 inserts the Application row.
    """
    source: str          # original CV filename (ChromaDB metadata key)
    cv_text: str         # Raw extracted text of the CV
    cosine_score: float  # Raw distance from ChromaDB similarity_search_with_score


class ExtractedCV(BaseModel):
    """
    Structured CV data extracted by the LLM (Node 2 output) OR reconstructed
    from existing ApplicationDetail rows for already-screened candidates.

    Identity fields (full_name, email, phone, linkedin_url) are extracted
    directly from the CV text and used in Node 4 to create the Candidate row.
    Professional fields are used by the scoring LLM and ApplicationDetail rows.
    raw_llm_output is kept for debugging/auditing and never written to the DB.

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
    # True  → Bucket A: candidate already has an application on this requisition.
    #         Node 4 will UPDATE scores/justifications only — no insert.
    # False → Bucket B: new candidate for this requisition.
    #         Node 4 will run full insert flow.
    is_existing_candidate: bool = False

    # Debug field — NOT persisted to DB
    raw_llm_output: Optional[str] = None


class ScoredCandidate(BaseModel):
    """
    Comparative scoring result for a single candidate (Node 3 output).

    combined_score is the weighted blend used for final ranking:
        combined = 0.40 * cosine_sim + 0.35 * (technical/10) + 0.25 * (behavioral/10)

    recommended_action drives the Application.status update in Node 4:
        "advance"      → SCREENING_PASSED
        "reject"       → SCREENING_REJECTED
        "needs_review" → status unchanged (manual review required)

    application_id is None until Node 4 creates/looks up the Application row
    and backfills it.  source is the stable CV filename key used throughout.
    """
    source: str                           # original CV filename
    application_id: Optional[int] = None  # set by Node 4

    # LLM-generated scores (0–10 scale)
    technical_score: float
    behavioral_score: float

    # Derived scores written to Application table
    combined_score: float           # weighted blend (0–1 scale)
    cosine_similarity_score: float  # normalised from ChromaDB distance (0–1 scale)

    # Narrative justifications written to ScreeningResult table
    technical_justification: str = ""
    behavioral_justification: str = ""
    overall_justification: str = ""

    # JSON arrays written to ScreeningResult table
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

    # ── INPUT (required, set by orchestrator before invoking subgraph) ────────
    requisition_id: int

    # ── NODE 1 OUTPUT ──────────────────────────────────────────────────────────
    job_description: Optional[str] = None
    top_candidates: List[CandidateDoc] = Field(default_factory=list)

    # ── NODE 2 OUTPUT ──────────────────────────────────────────────────────────
    # Full pool (Bucket A + Bucket B) — fed into Node 3 comparative scoring.
    extracted_cv_data: List[ExtractedCV] = Field(default_factory=list)

    # Source filenames that already have an application on this requisition.
    # Node 4 uses this to decide update-only vs full insert.
    existing_candidate_sources: Set[str] = Field(default_factory=set)

    # Bucket B only: maps extracted email → existing global candidate.id.
    # Populated when a freshly extracted email matches a candidate already in
    # the candidates table (from a different requisition).
    # Node 4 uses this to link the new application to the existing candidate
    # instead of creating a duplicate candidate row.
    email_to_candidate_id: Dict[str, int] = Field(default_factory=dict)

    # ── NODE 3 OUTPUT ──────────────────────────────────────────────────────────
    comparative_scores: List[ScoredCandidate] = Field(default_factory=list)

    # ── NODE 4 OUTPUT ──────────────────────────────────────────────────────────
    saved_count: int = 0    # new applications inserted
    updated_count: int = 0  # existing applications refreshed

    # ── ERROR TRACKING ─────────────────────────────────────────────────────────
    # Any node that encounters an unrecoverable error sets this field.
    # Subsequent nodes check this at entry and return immediately (fail-fast).
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True