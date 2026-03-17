"""
State schema for the RAG query subgraph.

Data flows sequentially through 3 nodes:
    query_processing → retrieval_and_context → response_generation

Each node reads fields from previous nodes and writes its own output fields.
The state is the single source of truth for the entire subgraph run.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# INTERMEDIATE DATA TYPES
# ============================================================================

class ExtractedFilters(BaseModel):
    """
    Filters extracted from the user's natural language query.
    
    These are used to narrow down retrieval results after the initial
    vector similarity search. All filters are optional.
    """
    candidate_name: Optional[str] = None
    """Explicit candidate name mentioned in query (e.g., 'John Smith')"""
    
    skills: List[str] = Field(default_factory=list)
    """Required technical skills/technologies (e.g., ['Python', 'React'])"""
    
    min_years_experience: Optional[float] = None
    """Minimum years of experience required"""
    
    max_years_experience: Optional[float] = None
    """Maximum years of experience"""
    
    min_combined_score: Optional[float] = None
    """Minimum combined screening score (0-1 scale)"""
    
    min_technical_score: Optional[float] = None
    """Minimum technical score (0-10 scale)"""
    
    min_assessment_score: Optional[float] = None
    """Minimum HackerRank assessment score"""


class ProcessedQuery(BaseModel):
    """
    Query processing result (Node 1 output).
    
    Contains the original query, a cleaned version for vectorization,
    the embedding vector, and extracted structured filters.
    """
    original_query: str
    """User's raw input query"""
    
    cleaned_query: str
    """Query with filter terms removed, ready for semantic search"""
    
    embedding: List[float]
    """Vector embedding of the cleaned query for ChromaDB search"""
    
    extracted_filters: ExtractedFilters
    """Structured filters parsed from the query"""


class CandidateMetadata(BaseModel):
    """
    Comprehensive candidate metadata retrieved from PostgreSQL (Node 2).
    
    This consolidates data from multiple tables:
    - Candidate (identity)
    - Application (scores, status, dates)
    - ApplicationDetail (skills, experience, education)
    - ScreeningResult (AI assessment)
    - InterviewSession (interview summaries)
    """
    candidate_id: int
    application_id: int
    
    # Identity fields
    full_name: str
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    # CV data
    cv_text: str
    """Full extracted CV text"""
    
    cv_summary: Optional[str] = None
    """LLM-generated summary from ApplicationDetail"""
    
    # Skills and experience
    skills: List[str] = Field(default_factory=list)
    """Technical/professional skills"""
    
    total_years_experience: Optional[float] = None
    education: List[Dict[str, str]] = Field(default_factory=list)
    """List of {degree, institution}"""
    
    previous_roles: List[Dict[str, Any]] = Field(default_factory=list)
    """List of {title, company, years}"""
    
    certifications: List[str] = Field(default_factory=list)
    
    # Screening scores
    cosine_similarity_score: Optional[float] = None
    technical_score: Optional[float] = None
    behavioral_score: Optional[float] = None
    combined_score: Optional[float] = None
    
    # Screening assessment
    key_strengths: List[str] = Field(default_factory=list)
    key_concerns: List[str] = Field(default_factory=list)
    technical_justification: Optional[str] = None
    behavioral_justification: Optional[str] = None
    recommended_action: Optional[str] = None
    
    # Assessment data
    assessment_score: Optional[float] = None
    assessment_completed_at: Optional[str] = None
    
    # Interview data
    interview_summary: Optional[str] = None
    """Most recent interview summary if available"""
    
    overall_interview_score: Optional[float] = None
    
    # ChromaDB relevance
    similarity_to_query: Optional[float] = None
    """Cosine similarity between query and candidate embedding"""


class RetrievalResult(BaseModel):
    """
    Vector search and metadata fetch result (Node 2 output).
    
    Contains all candidates that matched the query (after vector search
    and post-retrieval filtering), along with context size estimates.
    """
    matched_candidates: List[CandidateMetadata] = Field(default_factory=list)
    """Candidates that passed both vector search and filter criteria"""
    
    total_retrieved: int = 0
    """Total candidates from initial vector search"""
    
    total_after_filters: int = 0
    """Candidates remaining after applying extracted filters"""
    
    context_size_estimate: int = 0
    """Estimated token count for LLM context"""


class CitedCandidate(BaseModel):
    """
    A candidate mentioned in the LLM's response with a relevance snippet.
    """
    candidate_id: int
    application_id: int
    full_name: str
    relevance_snippet: str
    """Brief explanation of why this candidate was cited"""


class LLMResponse(BaseModel):
    """
    Final answer generated by the LLM (Node 3 output).
    
    Contains the natural language answer to the user's query,
    along with structured citations linking back to specific candidates.
    """
    answer: str
    """Natural language answer to the user's query"""
    
    cited_candidates: List[CitedCandidate] = Field(default_factory=list)
    """Candidates explicitly mentioned in the answer"""
    
    total_candidates_considered: int = 0
    """Number of candidates in the context provided to LLM"""
    
    confidence: Optional[str] = None
    """Optional confidence indicator: 'high', 'medium', 'low'"""


# ============================================================================
# MAIN SUBGRAPH STATE
# ============================================================================

class RAGQueryState(BaseModel):
    """
    Shared state for the RAG query subgraph.
    
    ┌───────────────────────────────────────────────────────────────────┐
    │  INPUT           │ query, requisition_id, user_id                 │
    ├──────────────────┼────────────────────────────────────────────────┤
    │  Node 1 output   │ processed_query                                │
    │  Node 2 output   │ retrieval_result                               │
    │  Node 3 output   │ llm_response                                   │
    ├──────────────────┼────────────────────────────────────────────────┤
    │  Error tracking  │ error (any node sets this to fail-fast)        │
    └───────────────────────────────────────────────────────────────────┘
    """
    
    # ── INPUT (required, set by orchestrator before invoking subgraph) ───────
    query: str
    """User's natural language question about candidates"""
    
    requisition_id: int
    """Requisition context for scoped search"""
    
    user_id: Optional[int] = None
    """User making the query (for access control and logging)"""
    
    # ── NODE 1 OUTPUT ─────────────────────────────────────────────────────────
    processed_query: Optional[ProcessedQuery] = None
    
    # ── NODE 2 OUTPUT ─────────────────────────────────────────────────────────
    retrieval_result: Optional[RetrievalResult] = None
    
    # ── NODE 3 OUTPUT ─────────────────────────────────────────────────────────
    llm_response: Optional[LLMResponse] = None
    
    # ── ERROR TRACKING ────────────────────────────────────────────────────────
    # Any node that encounters an unrecoverable error sets this field.
    # Subsequent nodes check this at entry and return immediately (fail-fast).
    error: Optional[str] = None
