"""
Data flows sequentially through 4 nodes:
    similarity_search → cv_extraction → comparative_scoring → save_results

Each node reads fields from previous nodes and writes its own output fields.
"""

from typing import Optional, List, Dict, Set
from pydantic import BaseModel, Field
from models.schemas import (
    CandidateDoc,
    ExtractedCV,
    ScoredCandidate
)

# ============================================================================
# MAIN SUBGRAPH STATE
# ============================================================================

class BatchScreeningState(BaseModel):
    """
    Node 1 output: JD, top candidates,
    Node 2 output: extracted CV data, extracted candidate score, email to candidate_id
    Node 3 output: comparative scores between all top candidates
    Node 4 output: Data saved to postgres database, saved count, updated count
    
    """

    # Input
    requisition_id: int

    # Node 1 Output
    job_description: Optional[str] = None
    top_candidates: List[CandidateDoc] = Field(default_factory=list)

    # Node 2 Output
    extracted_cv_data: List[ExtractedCV] = Field(default_factory=list)
    existing_candidate_sources: Set[str] = Field(default_factory=set)
    email_to_candidate_id: Dict[str, int] = Field(default_factory=dict)

    # Node 3 Output
    comparative_scores: List[ScoredCandidate] = Field(default_factory=list)

    # Node 4 output
    saved_count: int = 0
    updated_count: int = 0


    # ── ERROR TRACKING ─────────────────────────────────────────────────────────
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True