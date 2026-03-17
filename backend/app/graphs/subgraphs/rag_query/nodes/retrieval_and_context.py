"""
Node 2 — Retrieval and Context Building

Responsibilities:
- Perform ChromaDB vector similarity search using processed query embedding
- Fetch comprehensive candidate metadata from PostgreSQL for retrieved candidates
- Apply post-retrieval filters (name match, skills, experience, scores)
- Build structured LLM context with matched candidates
- Populate state.retrieval_result

Environment variables:
    INDEX_STORE_PATH (via load_vectordb.py) — ChromaDB persistence directory
"""

import logging
from typing import List

from ..state import RAGQueryState, RetrievalResult, CandidateMetadata
# TODO: Implement these functions once we have the ChromaDB and DB utilities ready
# from utils.load_vectordb import get_cv_vector_index
# from db.database import AsyncSessionLocal
# from db import crud

logger = logging.getLogger(__name__)


async def retrieval_and_context_node(state: RAGQueryState) -> RAGQueryState:
    """
    Node 2: Retrieve relevant candidates and build LLM context.
    
    Reads:
        state.processed_query — filters and embedding from Node 1
        state.requisition_id — scope for search
    
    Writes:
        state.retrieval_result — matched candidates with metadata
    
    Sets state.error on:
        - Missing processed_query
        - ChromaDB search failure
        - Database fetch failure
    """
    # ── Fail-fast: propagate upstream errors ──────────────────────────────────
    if state.error:
        return state
    
    if not state.processed_query:
        state.error = "[Node 2: retrieval_and_context] Missing processed_query from Node 1"
        logger.error(state.error)
        return state
    
    logger.info(
        f"[Node 2: retrieval_and_context] Starting retrieval for requisition {state.requisition_id}"
    )
    
    try:
        # ── Step 1: ChromaDB vector similarity search ─────────────────────────
        # TODO: Implement vector search
        # vector_index = get_cv_vector_index()
        # results = vector_index.similarity_search_with_score(
        #     query_embedding=state.processed_query.embedding,
        #     k=10,  # Retrieve top 10 candidates
        #     filter={"requisition_id": state.requisition_id}
        # )
        
        logger.info("[Node 2] Placeholder: Vector search not yet implemented")
        
        # ── Step 2: Fetch metadata from PostgreSQL ────────────────────────────
        # TODO: Implement database fetch
        # matched_candidates = []
        # async with AsyncSessionLocal() as db:
        #     for doc, similarity_score in results:
        #         candidate_metadata = await _fetch_candidate_metadata(
        #             db, doc.metadata, similarity_score
        #         )
        #         matched_candidates.append(candidate_metadata)
        
        matched_candidates: List[CandidateMetadata] = []
        
        # ── Step 3: Apply post-retrieval filters ──────────────────────────────
        filtered_candidates = _apply_filters(
            matched_candidates,
            state.processed_query.extracted_filters
        )
        
        logger.info(
            f"[Node 2] Retrieved {len(matched_candidates)} candidates, "
            f"{len(filtered_candidates)} after filtering"
        )
        
        # ── Step 4: Estimate context size ─────────────────────────────────────
        context_size = _estimate_context_size(filtered_candidates)
        
        # ── Step 5: Populate state ─────────────────────────────────────────────
        state.retrieval_result = RetrievalResult(
            matched_candidates=filtered_candidates,
            total_retrieved=len(matched_candidates),
            total_after_filters=len(filtered_candidates),
            context_size_estimate=context_size,
        )
        
        logger.info(
            f"[Node 2] Retrieval complete: {len(filtered_candidates)} candidates, "
            f"~{context_size} tokens"
        )
        return state
        
    except Exception as exc:
        state.error = f"[Node 2: retrieval_and_context] Failed: {exc}"
        logger.error(state.error, exc_info=True)
        return state


# ── Helper Functions ──────────────────────────────────────────────────────────

def _apply_filters(
    candidates: List[CandidateMetadata],
    filters
) -> List[CandidateMetadata]:
    """
    Apply post-retrieval filters to candidate list.
    
    Filters applied:
    - Candidate name match (case-insensitive substring)
    - Required skills (all must be present)
    - Experience range
    - Minimum scores (combined, technical, assessment)
    """
    filtered = candidates
    
    # Name filter
    if filters.candidate_name:
        name_lower = filters.candidate_name.lower()
        filtered = [
            c for c in filtered
            if name_lower in c.full_name.lower()
        ]
    
    # Skills filter (all required skills must be present)
    if filters.skills:
        required_skills_lower = [s.lower() for s in filters.skills]
        filtered = [
            c for c in filtered
            if all(
                any(req in skill.lower() for skill in c.skills)
                for req in required_skills_lower
            )
        ]
    
    # Experience filter
    if filters.min_years_experience is not None:
        filtered = [
            c for c in filtered
            if c.total_years_experience is not None
            and c.total_years_experience >= filters.min_years_experience
        ]
    
    if filters.max_years_experience is not None:
        filtered = [
            c for c in filtered
            if c.total_years_experience is not None
            and c.total_years_experience <= filters.max_years_experience
        ]
    
    # Score filters
    if filters.min_combined_score is not None:
        filtered = [
            c for c in filtered
            if c.combined_score is not None
            and c.combined_score >= filters.min_combined_score
        ]
    
    if filters.min_technical_score is not None:
        filtered = [
            c for c in filtered
            if c.technical_score is not None
            and c.technical_score >= filters.min_technical_score
        ]
    
    if filters.min_assessment_score is not None:
        filtered = [
            c for c in filtered
            if c.assessment_score is not None
            and c.assessment_score >= filters.min_assessment_score
        ]
    
    return filtered


def _estimate_context_size(candidates: List[CandidateMetadata]) -> int:
    """
    Estimate total token count for LLM context.
    
    Rough heuristics:
    - CV summary: ~200 tokens
    - Skills list: ~50 tokens
    - Scores/justifications: ~100 tokens
    - Total per candidate: ~350 tokens
    """
    return len(candidates) * 350
